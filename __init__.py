
try:
    import sys,bpy,math,traceback,os
    import bpy.utils.previews
except:
    pass

bl_info = {
    "name": "Collection Instancer",
    "description": "Tool to better access collection for instancing",
    "author": "Thomas Trocha",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "View3D",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Object" }

ICON_SIZE = 128

def load_icons(key,folder):
    pcoll = preview_collections.get(key)
    if not pcoll:
        pcoll = bpy.utils.previews.new()
        preview_collections[key]=pcoll


    directory = os.fsencode(folder)
    
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".png") or filename.endswith(".jpg"): 
            imgpath = os.path.join(folder, filename)
            print("loading image %s | %s" % (filename,imgpath))
            pcoll.load(filename,imgpath,"IMAGE")

def get_image_lib(key):
    return preview_collections.get(key)

def has_tile_creator_addon():
    return "addon_tilemap_creator" in bpy.context.preferences.addons

def parent_collection_to_csv_children(parent_collection,collection_names="",recursive=False):
    for child in parent_collection.children:
        if child:
            collection_names = child.name if collection_names=="" else "%s,%s"%(collection_names,child.name)
            if recursive and len(child.children)>0:
                collection_names = parent_collection_to_csv_children(child,collection_names,True)
    return collection_names

class CIO_COLLECTION_TYPE(bpy.types.PropertyGroup):
    collection : bpy.props.PointerProperty(type=bpy.types.Collection)


class CIO_HIERARCHY(bpy.types.PropertyGroup):
    active          : bpy.props.BoolProperty(default=True)
    collection_path : bpy.props.CollectionProperty(type=CIO_COLLECTION_TYPE)
    icon_scale  : bpy.props.FloatProperty()    

class CIO_WRLD_Settings(bpy.types.PropertyGroup):
    show_manage_hierachy_menu : bpy.props.BoolProperty(name="Hierarchy Manager",default=False)
    hierarchies : bpy.props.CollectionProperty(type=CIO_HIERARCHY)
    icon_folder : bpy.props.StringProperty(subtype="DIR_PATH")
    float       


CIO_OP_ADD_HIERARCHY = "add_hierarchy"
CIO_OP_DEL_HIERARCHY = "del_hierarchy"
CIO_OP_ADD_HIERARCHY_ITEM = "add_hierarchy_item"
CIO_OP_MOVEBACK_HIERARCHY_ITEM = "moveback_hierarchy_item"
CIO_OP_CREATE_INSTANCE = "create_instance"
CIO_OP_CREATE_TILE_PREVIEW = "render_tile_previews"
CIO_OP_LOAD_TILE_PREVIEWS = "load_tile_previews"


preview_collections = {}

class CIO_OT_Manage_hierarchies(bpy.types.Operator):
    """"""

    bl_idname = "cio.manage_hierarchies"
    bl_label = "Manage Hierarchies"

    operation : bpy.props.StringProperty() # operation as string
    idx       : bpy.props.IntProperty()    # generic idx-value
    hidx      : bpy.props.IntProperty()    # hierarchy idx
    col_name  : bpy.props.StringProperty() # col_name as string

    def execute(self, context):
        settings = bpy.context.scene.world.cioSettings
        if self.operation==CIO_OP_ADD_HIERARCHY:
            new_h = settings.hierarchies.add()
            top_level_item = new_h.collection_path.add()
        elif self.operation==CIO_OP_DEL_HIERARCHY:
            try:
                settings.hierarchies.remove(self.idx);
            except Exception:
                print("Error on %s: idx:%s " % (CIO_OP_DEL_HIERARCHY,self.idx))
                traceback.print_exc()

        elif self.operation==CIO_OP_ADD_HIERARCHY_ITEM:
            try:
                col = bpy.data.collections[self.col_name]
                hierarchy = settings.hierarchies[self.hidx]
                new_hitem = hierarchy.collection_path.add()
                new_hitem.collection = col
            except Exception:
                print("Error on %s: col_name:%s hidx:%s " % (CIO_OP_ADD_HIERARCHY_ITEM,self.col_name,self.hidx))
                traceback.print_exc()

        elif self.operation==CIO_OP_MOVEBACK_HIERARCHY_ITEM:
            try:
                hierarchy = settings.hierarchies[self.hidx]
                del_idx = self.idx+1
                # remove data behind the position be moved to
                while del_idx < len(hierarchy.collection_path):
                    hierarchy.collection_path.remove(del_idx)

            except Exception:
                print("Error on %s: hidx:%s idx:%s " % (CIO_OP_MOVEBACK_HIERARCHY_ITEM,self.hidx,self.idx))
                traceback.print_exc()
        elif self.operation==CIO_OP_CREATE_INSTANCE:
            try:
                cursor_position = bpy.context.scene.cursor.location
                bpy.ops.object.collection_instance_add(collection=self.col_name, align='WORLD', location=cursor_position, scale=(1, 1, 1))

            except Exception:
                print("Error on %s: col_name:%s " % (CIO_OP_CREATE_INSTANCE,self.col_name))
                traceback.print_exc()
        elif self.operation==CIO_OP_CREATE_TILE_PREVIEW:
            hierarchy = settings.hierarchies[self.hidx]

            icon_path = bpy.path.abspath(settings.icon_folder)

            item = hierarchy.collection_path[0]
            col = item.collection
            if col:
                output_path_iso = "%s/%s/iso" % (icon_path,col.name)
                output_path_top = "%s/%s/top" % (icon_path,col.name)
                col_names = parent_collection_to_csv_children(col,"",True)

                bpy.ops.tmc.render_tiles(scene_name="tilemap_scene"
                                ,col_names=col_names
                                ,output_folder=output_path_iso
                                ,render_width=ICON_SIZE
                                ,render_height=ICON_SIZE
                                ,cam_delta_scale=hierarchy.icon_scale
                                ,remove_scene=True)

                bpy.ops.tmc.render_tiles(scene_name="tilemap_scene"
                                ,col_names=col_names
                                ,output_folder=output_path_top
                                ,render_width=ICON_SIZE
                                ,render_height=ICON_SIZE
                                ,cam_delta_scale=hierarchy.icon_scale
                                ,cam_preset="cam_top_down"
                                ,remove_scene=True)                                

        elif self.operation==CIO_OP_LOAD_TILE_PREVIEWS:
            icon_path = bpy.path.abspath(settings.icon_folder)

            for hierarchy in settings.hierarchies:
                if len(hierarchy.collection_path)>0:
                    col = hierarchy.collection_path[0].collection
                    if col:
                        input_path_iso = "%s/%s/iso/%s_%s" % (icon_path, col.name, ICON_SIZE,ICON_SIZE)
                        input_path_top = "%s/%s/top/%s_%s" % (icon_path, col.name, ICON_SIZE,ICON_SIZE)
                        
                        print("TRY TO LOAD %s | %s" %(input_path_iso,col.name))
                        load_icons("%s_top"%col.name,input_path_top)
                        load_icons("%s_iso"%col.name,input_path_iso)

        return{'FINISHED'}


class CIO_PT_main(bpy.types.Panel):
    bl_idname = "CIO_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Collection Instances"
    bl_label ="Instance Organizer"
    

    #bl_options = {'DEFAULT_CLOSED'}
    
    # @classmethod
    # def poll(cls, context):
    #     return bpy.context.scene.render.engine=="CYCLES"   
    # 

    @classmethod
    def poll(cls, context):
        return True


    def draw_hierarchy(self, hidx,hierarchy, layout):
        if not hierarchy:
            return

        current_collection = None
        points = ""
        # draw breadcrumbs
        box = layout.box()

        bc_box = box.box()
        amount_col_paths = len(hierarchy.collection_path)
        for idx,col in enumerate(hierarchy.collection_path):
            col = col.collection
            if not col:
                continue
            #icon = "NONE" if len(col.children)>0 else "ADD"
            
            row = bc_box.row()

            op = row.operator("cio.manage_hierarchies",text=col.name)
            op.operation = CIO_OP_MOVEBACK_HIERARCHY_ITEM
            op.hidx=hidx
            op.idx=idx

            current_collection = col

            if idx==0:
                row.prop(hierarchy,"active",text="")
                if not hierarchy.active:
                    return
            

        if not current_collection:
            return

        root_name = hierarchy.collection_path[0].collection.name
        iso_img_lib = get_image_lib("%s_iso"%root_name)
        top_img_lib = get_image_lib("%s_top"%root_name)
        
        if iso_img_lib:
            print("FOUND IMAGE LIB: %s" % root_name)
        else:
            print("COULD NOT FIND IMG LIB:%s" % root_name)

        # draw collection-children of current collection
        with_children_box = box.box()
        without_children_box = box.box()
        without_children_amount=0
        for idx,col in enumerate(current_collection.children):
            if len(col.children)>0:
                row = with_children_box.row()
                op = row.operator("cio.manage_hierarchies",text=col.name) 
                op.operation = CIO_OP_ADD_HIERARCHY_ITEM
                op.col_name = col.name
                op.hidx = hidx

                op = row.operator("cio.manage_hierarchies",text="",icon="OUTLINER_OB_GROUP_INSTANCE")
                op.operation=CIO_OP_CREATE_INSTANCE
                op.col_name=col.name 
            else:
                row = without_children_box.row()
                col_icon_iso = None
                col_icon_top = None
                if iso_img_lib:
                    col_icon_iso = iso_img_lib.get("%s.png"%col.name)
                    col_icon_top = top_img_lib.get("%s.png"%col.name)

                if col_icon_iso:
                    row.label(text=col.name,icon_value=col_icon_iso.icon_id)
                    row=without_children_box.row()
                    row.template_icon(icon_value=col_icon_iso.icon_id,scale=6.0)
                    row.template_icon(icon_value=col_icon_top.icon_id,scale=6.0)
                else:
                    row.label(text=col.name)

                op = row.operator("cio.manage_hierarchies",text="",icon="OUTLINER_OB_GROUP_INSTANCE")
                op.operation=CIO_OP_CREATE_INSTANCE
                op.col_name=col.name 
                without_children_amount = without_children_amount + 1
                


    def draw(self, context):
        layout = self.layout

        if not bpy.context.scene.world:
            row = layout.row()
            row.label(text="Please set a world!")
            return
            
        settings = bpy.context.scene.world.cioSettings

        row = layout.row()

        row.label(text="Collection Instancer")
        row = layout.row()
        box = row.box()
        row = box.row()
        row.prop(settings,"show_manage_hierachy_menu")
        row = box.row()
        # icons: ADD,REMOVE,OUTLINER_OB_GROUP_INSTANCE,GROUP

        has_tile_addon = has_tile_creator_addon()

        if settings.show_manage_hierachy_menu:
            innerbox = row.box()

            for idx,hierarchy in enumerate(settings.hierarchies):
                col_path = hierarchy.collection_path

                row = innerbox.row()
                row.prop(col_path[0],"collection")
                op = row.operator("cio.manage_hierarchies",icon="REMOVE",text="")
                op.operation = CIO_OP_DEL_HIERARCHY
                op.idx = idx

                if has_tile_addon:
                    col = row.column()
                    op = col.operator("cio.manage_hierarchies",icon="RENDERLAYERS",text="")
                    op.operation = CIO_OP_CREATE_TILE_PREVIEW
                    op.hidx = idx
                    if not settings.icon_folder:
                        col.enabled=False

                    row = innerbox.row()
                    row.prop(hierarchy,"icon_scale",text="icon scale delta")

            row = box.row()
            row.prop(settings,"icon_folder")
            col = row.column()
            op = col.operator("cio.manage_hierarchies",icon="FILE_REFRESH",text="")
            op.operation = CIO_OP_LOAD_TILE_PREVIEWS
            if not settings.icon_folder:
                col.enabled=False

            row = box.row()
            row.operator("cio.manage_hierarchies",icon="ADD",text="").operation=CIO_OP_ADD_HIERARCHY
            


        for hidx,hierarchy in enumerate(settings.hierarchies):
            self.draw_hierarchy(hidx,hierarchy,layout)       


classes =(
        # Data
        CIO_COLLECTION_TYPE,
        CIO_HIERARCHY,
        CIO_WRLD_Settings,
        # Operations
        CIO_OT_Manage_hierarchies,
        # UI
        CIO_PT_main
)

defRegister, defUnregister = bpy.utils.register_classes_factory(classes)

def register():
    defRegister()
    bpy.types.World.cioSettings = bpy.props.PointerProperty(type=CIO_WRLD_Settings)
    
def unregister():
    defUnregister()
    del bpy.types.World.cioSettings
    