
try:
    import sys,bpy,math,traceback
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


class CIO_COLLECTION_TYPE(bpy.types.PropertyGroup):
    collection : bpy.props.PointerProperty(type=bpy.types.Collection)

class CIO_HIERARCHY(bpy.types.PropertyGroup):
    active          : bpy.props.BoolProperty(default=True)
    collection_path : bpy.props.CollectionProperty(type=CIO_COLLECTION_TYPE)

class CIO_WRLD_Settings(bpy.types.PropertyGroup):
    show_manage_hierachy_menu : bpy.props.BoolProperty(name="Hierarchy Manager",default=False)
    hierarchies : bpy.props.CollectionProperty(type=CIO_HIERARCHY)


CIO_OP_ADD_HIERARCHY = "add_hierarchy"
CIO_OP_DEL_HIERARCHY = "del_hierarchy"
CIO_OP_ADD_HIERARCHY_ITEM = "add_hierarchy_item"
CIO_OP_MOVEBACK_HIERARCHY_ITEM = "moveback_hierarchy_item"
CIO_OP_CREATE_INSTANCE = "create_instance"

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
                row.label(text=col.name)
                op = row.operator("cio.manage_hierarchies",text="",icon="OUTLINER_OB_GROUP_INSTANCE")
                op.operation=CIO_OP_CREATE_INSTANCE
                op.col_name=col.name 
                without_children_amount = without_children_amount + 1
                


    def draw(self, context):
        settings = bpy.context.scene.world.cioSettings

        layout = self.layout
        row = layout.row()

        row.label(text="Collection Instancer")
        row = layout.row()
        box = row.box()
        row = box.row()
        row.prop(settings,"show_manage_hierachy_menu")
        row = box.row()
        # icons: ADD,REMOVE,OUTLINER_OB_GROUP_INSTANCE,GROUP

        if settings.show_manage_hierachy_menu:
            innerbox = row.box()
    
            for idx,hierarchy in enumerate(settings.hierarchies):
                col_path = hierarchy.collection_path

                row = innerbox.row()
                row.prop(col_path[0],"collection")
                op = row.operator("cio.manage_hierarchies",icon="REMOVE",text="")
                op.operation = CIO_OP_DEL_HIERARCHY
                op.idx = idx

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
    