import bpy
import traceback,sys


class TMC_Operations:
    TMC_OP_CREATE_TILEMAP = "create_tilemap"
    TMC_OP_DELETE_TILEMAP = "delete_tilemap"
    TMC_OP_ADD_ROOT_COLLECTION = "add_collection"
    TMC_OP_REMOVE_ROOT_COLLECTION = "remove_collection"
    TMC_OP_REQUEST_RENDER = "request_render"

    TMC_CAM_PRESET_TOPDOWN = "cam_top_down"    # top down
    TMC_CAM_PRESET_FRONTAL45 = "cam_frontal45" # looking diagonal frontal on tile
    TMC_CAM_PRESET_ISO = "cam_iso"             # iso. (is this iso?)

def parent_collection_to_csv_children(parent_collection,collection_names="",recursive=False):
    for sub_col in parent_collection:
        if sub_col.collection:
            for child in sub_col.collection.children:
                collection_names = child.name if collection_names=="" else "%s,%s"%(collection_names,child.name)
                if recursive and len(child.children)>0:
                    collection_names = parent_collection_to_csv_children(child,collection_names,True)
    return collection_names

class TMC_OT_CRUD_tilemaps(bpy.types.Operator):
    """ CRUD Tilemap """

    bl_idname = "tmc.manage_tilemaps"
    bl_label = "Tilemap Operation"

    operation : bpy.props.StringProperty() 
    idx       : bpy.props.IntProperty()
    cidx      : bpy.props.IntProperty()

    def execute(self, context):
        settings = bpy.context.scene.tmcSettings

        if self.operation==TMC_Operations.TMC_OP_CREATE_TILEMAP:
            settings.tilemaps.add()

        elif self.operation==TMC_Operations.TMC_OP_DELETE_TILEMAP:
            settings.tilemaps.remove(self.idx) 

        elif self.operation==TMC_Operations.TMC_OP_ADD_ROOT_COLLECTION:
            tilemap = settings.tilemaps[self.idx]
            tilemap.parent_collections.add()

        elif self.operation==TMC_Operations.TMC_OP_REMOVE_ROOT_COLLECTION:
            tilemap = settings.tilemaps[self.idx]
            tilemap.parent_collections.remove(self.cidx)

        elif self.operation==TMC_Operations.TMC_OP_REQUEST_RENDER:
            tilemap = settings.tilemaps[self.idx]
            collection_names = ""

            print("collection_name:%s" % collection_names)
            bpy.ops.tmc.render_tiles(scene_name="tilemap_scene"
                                        ,col_names=collection_names
                                        ,output_folder=tilemap.output_path
                                        ,render_width=tilemap.render_size[0]
                                        ,render_height=tilemap.render_size[1]
                                        ,cam_delta_scale=tilemap.cam_delta_scale
                                        ,remove_scene=True)

        return{'FINISHED'}      


class TMC_OT_Render_tiles(bpy.types.Operator):
    """ Render Tilemap """

    bl_idname = "tmc.render_tiles"
    bl_label = "Tilemap Operation"

    scene_name      : bpy.props.StringProperty()
    col_names       : bpy.props.StringProperty()
    render_width    : bpy.props.IntProperty(default=512)
    render_height   : bpy.props.IntProperty(default=512)
    output_folder   : bpy.props.StringProperty()
    cam_preset      : bpy.props.StringProperty(default=TMC_Operations.TMC_CAM_PRESET_ISO)
    remove_scene    : bpy.props.BoolProperty(default=False)
    cam_delta_scale : bpy.props.FloatProperty()

    def set_camera_preset(self,cam,preset):
        if preset == TMC_Operations.TMC_CAM_PRESET_FRONTAL45:
            cam.location = (0.0, -20.0, 20.0)
            cam.rotation_euler = (0.7853981852531433, -0.0, 0.0)
        #TopDown
        elif preset == TMC_Operations.TMC_CAM_PRESET_TOPDOWN:
            cam.location = (0.0, 0, 28.18587303161621)
            cam.rotation_euler = (0,0,0)
        #iso?
        elif preset == TMC_Operations.TMC_CAM_PRESET_ISO:
            cam.location = (-20.0, -20.0, 28.18587303161621)
            cam.rotation_euler = (0.7853981852531433, -0.0, -0.7853981852531433)
        else:
            print("ERROR: Tilemap Operation: Unknown camera-presetion %s! Using iso-preset!" % self.cam_preset)       
            set_camera_preset(TMC_Operations.TMC_CAM_PRESET_ISO)


    def setup_scene(self, context):
        sname = "__tilemap_scene" if not self.scene_name else self.scene_name
        tilemap_scene = bpy.data.scenes.new(sname)
        bpy.context.window.scene = tilemap_scene
        
        # create camera
        cam = bpy.data.cameras.new("__tilemap_cam")
        cam.type="ORTHO"
        cam.ortho_scale = 6.0 + self.cam_delta_scale

        camnode = bpy.data.objects.new("__timemap_camnode",cam)
        self.set_camera_preset(camnode,self.cam_preset)

        tilemap_scene.camera = camnode

        tilemap_scene.collection.objects.link(camnode)
        # create light
        light = bpy.data.lights.new("__tilemap_light","SUN")
        light.energy=5
        light.specular_factor=0.01
        lightnode = bpy.data.objects.new("__tilemape_lightnode",light)
        lightnode.rotation_euler=(0.6503279805183411, 0.055217113345861435, 1.8663908243179321)
        tilemap_scene.collection.objects.link(lightnode)   
        return tilemap_scene     

    def execute(self, context):
        #settings = bpy.context.scene.tmcSettings

        before_scene = bpy.context.scene
        
        try:
            scene = None
            if self.scene_name and self.scene_name in bpy.data.scenes:
                scene = bpy.data.scenes[self.scene_name]
                bpy.context.window.scene = scene
                if "tile" in bpy.data.objects:
                    bpy.data.objects.remove(bpy.data.objects["tile"]) # remove old tile
            else:                    
                scene = self.setup_scene(context)

            bpy.context.scene.render.resolution_x = self.render_width
            bpy.context.scene.render.resolution_y = self.render_height
            bpy.context.scene.render.film_transparent = True

            colnames = self.col_names.split(",")

            for col_name in colnames:
                col_name = col_name.strip() 
                if col_name not in bpy.data.collections:
                    print("Unknown collection:%s" % col_name)
                    continue

                bpy.ops.object.collection_instance_add(collection=col_name, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
                current_tile = bpy.context.active_object

                bpy.ops.render.render()
                render_image = bpy.data.images["Render Result"]
                filepath = "%s/%s_%s/%s.png" % (self.output_folder,self.render_width,self.render_height,col_name)
                render_image.save_render(filepath)
                bpy.data.objects.remove(current_tile) # remove old tile

            if self.remove_scene:
                bpy.data.scenes.remove(scene)

        except Exception:
            print("ERROR: Tilemap Operation [%s]: scene_name:%s col_name:%s width:%s height:%s" % ( "Render Tilemap",self.scene_name,self.col_name,self.render_width,self.render_height ))
            traceback.print_exc()

        # finally:
        #     bpy.context.window.scene = before_scene
                


        return{'FINISHED'}

