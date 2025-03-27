from itertools import islice
import bpy
import bmesh

class SelectByIndex(bpy.types.Operator):
    """Select all vertices, edges, or faces within an index range"""
    bl_idname = "mesh.select_by_index"
    bl_label = "Select By Index"
    bl_options = {'REGISTER', 'UNDO'}

    select_mode: bpy.props.EnumProperty(
        name="Select Mode",
        description="Choose a selection mode",
        items=[
            ('VERTEX', "Vertex", "Select vertices"),
            ('EDGE', "Edge", "Select edges"),
            ('FACE', "Face", "Select faces"),
        ]
    )

    input_mode: bpy.props.EnumProperty(
        name="Input Mode",
        description="Choose the selection range inputs",
        items=[
            ('INCLUSIVE', "Inclusive", "Input start index and inclusive stop index"),
            ('EXCLUSIVE', "Exclusive", "Input start index and exclusive stop index"),
            ('COUNT', "Count", "Input start index and selection count"),
        ]
    )
    
    count: bpy.props.IntProperty(
        name="Count",
        description="The count of items for the selection range",
        default=1,
        min=1
    )

    private_start: bpy.props.IntProperty(default=0, min=0)

    def update_start(self, context):
        if self.input_mode != 'COUNT':
            self.count = max(self.count + self.private_start - self.start, 1)
        self.private_start = self.start

    start: bpy.props.IntProperty(
        name="Start",
        description="The starting index for the selection range",
        default=0,
        min=0,
        update=update_start
    )

    def get_inc_stop(self):
        return self.start + self.count - 1

    def get_exc_stop(self):
        return self.start + self.count

    def set_inc_stop(self, value):
        value = max(value, 0)
        if self.input_mode != 'COUNT' and value < self.start:
            self.start = value
            self.count = 1
        else:
            self.count = 1 + value - self.start

    def set_exc_stop(self, value):
        value = max(value, 1)
        if self.input_mode != 'COUNT' and value <= self.start:
            self.start = value - 1
            self.count = 1
        else:
            self.count = value - self.start
    
    inc_stop: bpy.props.IntProperty(
        name="Stop",
        description="The inclusive ending index for the selection range",
        default=0,
        min=0,
        get=get_inc_stop,
        set=set_inc_stop
    )
    
    exc_stop: bpy.props.IntProperty(
        name="Stop",
        description="The exclusive ending index for the selection range",
        default=1,
        min=1,
        get=get_exc_stop,
        set=set_exc_stop
    )

    replace_selection: bpy.props.BoolProperty(
        name="Replace Selection",
        description="Replace instead of adding to the previous selection",
        default=True
    )

    @classmethod
    def poll(cls, context):
        if context.object.mode == 'EDIT':
            return True
        cls.poll_message_set("The active object must be in Edit mode")
        return False

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(self, "select_mode")
        layout.prop(self, "input_mode")
        layout.prop(self, "start")
        
        if self.input_mode == 'INCLUSIVE':
            layout.prop(self, "inc_stop")
        elif self.input_mode == 'EXCLUSIVE':
            layout.prop(self, "exc_stop")
        elif self.input_mode == 'COUNT':
            layout.prop(self, "count")
        
        layout.prop(self, "replace_selection")

    def check(self, context):
        bm = bmesh.from_edit_mesh(context.object.data)

        if self.select_mode == 'VERTEX':
            max_len = len(bm.verts)
        elif self.select_mode == 'EDGE':
            max_len = len(bm.edges)
        elif self.select_mode == 'FACE':
            max_len = len(bm.faces)

        bm.free()

        max_start = max(max_len - 1, 0)
        start = self.start
        stop = self.inc_stop

        if start > max_start or stop > max_start:
            self.start = min(start, max_start)
            self.inc_stop = min(stop, max_start)
            return True

        return False

    def execute(self, context):
        if self.replace_selection:
            bpy.ops.mesh.select_all(action='DESELECT')

        me = context.object.data
        bm = bmesh.from_edit_mesh(me)

        if self.select_mode == 'VERTEX':
            bpy.ops.mesh.select_mode(type='VERT')
            selectable_items = bm.verts
        elif self.select_mode == 'EDGE':
            bpy.ops.mesh.select_mode(type='EDGE')
            selectable_items = bm.edges
        elif self.select_mode == 'FACE':
            bpy.ops.mesh.select_mode(type='FACE')
            selectable_items = bm.faces

        for item in islice(selectable_items, self.start, self.exc_stop):
            item.select = True
        
        bm.select_flush_mode()
        bm.free()
        bmesh.update_edit_mesh(me)

        return {'FINISHED'}
        
    def invoke(self, context, event):
        if context.tool_settings.mesh_select_mode[0]:  # Vertex mode
            self.select_mode = 'VERTEX'
        elif context.tool_settings.mesh_select_mode[1]:  # Edge mode
            self.select_mode = 'EDGE'
        elif context.tool_settings.mesh_select_mode[2]:  # Face mode
            self.select_mode = 'FACE'

        self.check(context)
        
        return self.execute(context)

def menu_func(self, context):
    self.layout.operator(SelectByIndex.bl_idname, text="By Index")

def register():
    bpy.utils.register_class(SelectByIndex)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(menu_func)

def unregister():
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(menu_func)
    bpy.utils.unregister_class(SelectByIndex)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()