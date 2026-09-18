"""Step 1 - procedural base heightfield (Geometry Nodes).

Builds an object `Terrain` driven by a `SOV_Terrain_Base` node group: a grid
whose vertices are pushed along Z by a noise texture. Nothing is baked into
the mesh, so every value stays adjustable on the modifier afterwards.

Run:
    blender --python blender/terrain/01_base_heightfield.py

or open the file in Blender's Scripting workspace and press Run.

Re-running replaces the previous object and node group. Nothing else in the
scene is touched.
"""

import bpy

OBJECT_NAME = "Terrain"
NODE_GROUP_NAME = "SOV_Terrain_Base"

# name, socket type, default, soft min, soft max
GROUP_INPUTS = (
    ("Size", "NodeSocketFloat", 20.0, 0.01, 10000.0),
    ("Resolution", "NodeSocketInt", 128, 2, 2048),
    ("Height", "NodeSocketFloat", 3.0, 0.0, 10000.0),
    ("Noise Scale", "NodeSocketFloat", 1.5, 0.0, 1000.0),
    ("Detail", "NodeSocketFloat", 8.0, 0.0, 15.0),
    ("Roughness", "NodeSocketFloat", 0.5, 0.0, 1.0),
    ("Seed", "NodeSocketFloat", 0.0, -10000.0, 10000.0),
)


def socket(node, name, output=False):
    """Look a socket up by name, failing loudly with the real options.

    Math and Vector Math nodes repeat the same socket name, so those are
    addressed by index at the call site instead.
    """
    sockets = node.outputs if output else node.inputs
    if name in sockets:
        return sockets[name]
    side = "output" if output else "input"
    available = ", ".join(repr(s.name) for s in sockets)
    raise KeyError(
        "%s node has no %s socket %r on this Blender build. Available: %s"
        % (node.bl_idname, side, name, available)
    )


def add_group_socket(group, name, in_out, socket_type):
    """Add an interface socket, supporting both the 4.x and 3.x APIs."""
    if hasattr(group, "interface"):  # Blender 4.0+
        return group.interface.new_socket(
            name=name, in_out=in_out, socket_type=socket_type
        )
    collection = group.inputs if in_out == "INPUT" else group.outputs
    return collection.new(socket_type, name)


def clear_previous():
    """Remove the object and node group this script owns, if they exist."""
    obj = bpy.data.objects.get(OBJECT_NAME)
    if obj is not None:
        mesh = obj.data
        bpy.data.objects.remove(obj)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    group = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if group is not None:
        bpy.data.node_groups.remove(group)


def build_node_group():
    group = bpy.data.node_groups.new(NODE_GROUP_NAME, "GeometryNodeTree")

    add_group_socket(group, "Geometry", "OUTPUT", "NodeSocketGeometry")
    for name, socket_type, default, soft_min, soft_max in GROUP_INPUTS:
        item = add_group_socket(group, name, "INPUT", socket_type)
        item.default_value = default
        item.min_value = soft_min
        item.max_value = soft_max

    nodes = group.nodes
    links = group.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-900, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (700, 0)

    grid = nodes.new("GeometryNodeMeshGrid")
    grid.location = (-600, 220)

    position = nodes.new("GeometryNodeInputPosition")
    position.location = (-900, -300)

    # Offsetting the sample position by the seed gives a different landscape
    # per seed without touching the noise node's dimensionality.
    seed_offset = nodes.new("ShaderNodeCombineXYZ")
    seed_offset.location = (-600, -420)
    seed_offset.inputs["Z"].default_value = 0.0

    sample_position = nodes.new("ShaderNodeVectorMath")
    sample_position.operation = "ADD"
    sample_position.location = (-420, -300)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-230, -200)

    # Noise returns 0..1, so centre it before scaling to keep the terrain
    # sitting on the object origin rather than floating above it.
    centre = nodes.new("ShaderNodeMath")
    centre.operation = "SUBTRACT"
    centre.location = (40, -200)
    centre.inputs[1].default_value = 0.5

    scale_height = nodes.new("ShaderNodeMath")
    scale_height.operation = "MULTIPLY"
    scale_height.location = (220, -200)

    offset = nodes.new("ShaderNodeCombineXYZ")
    offset.location = (400, -200)

    set_position = nodes.new("GeometryNodeSetPosition")
    set_position.location = (220, 220)

    shade_smooth = nodes.new("GeometryNodeSetShadeSmooth")
    shade_smooth.location = (480, 220)

    links.new(socket(group_in, "Size", output=True), socket(grid, "Size X"))
    links.new(socket(group_in, "Size", output=True), socket(grid, "Size Y"))
    links.new(socket(group_in, "Resolution", output=True), socket(grid, "Vertices X"))
    links.new(socket(group_in, "Resolution", output=True), socket(grid, "Vertices Y"))

    links.new(socket(group_in, "Seed", output=True), socket(seed_offset, "X"))
    links.new(socket(group_in, "Seed", output=True), socket(seed_offset, "Y"))

    links.new(socket(position, "Position", output=True), sample_position.inputs[0])
    links.new(socket(seed_offset, "Vector", output=True), sample_position.inputs[1])
    links.new(socket(sample_position, "Vector", output=True), socket(noise, "Vector"))

    links.new(socket(group_in, "Noise Scale", output=True), socket(noise, "Scale"))
    links.new(socket(group_in, "Detail", output=True), socket(noise, "Detail"))
    links.new(socket(group_in, "Roughness", output=True), socket(noise, "Roughness"))

    links.new(socket(noise, "Fac", output=True), centre.inputs[0])
    links.new(centre.outputs[0], scale_height.inputs[0])
    links.new(socket(group_in, "Height", output=True), scale_height.inputs[1])
    links.new(scale_height.outputs[0], socket(offset, "Z"))

    links.new(socket(grid, "Mesh", output=True), socket(set_position, "Geometry"))
    links.new(socket(offset, "Vector", output=True), socket(set_position, "Offset"))
    links.new(
        socket(set_position, "Geometry", output=True), socket(shade_smooth, "Geometry")
    )
    links.new(socket(shade_smooth, "Geometry", output=True), group_out.inputs[0])

    return group


def build_object(group):
    mesh = bpy.data.meshes.new(OBJECT_NAME)
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    bpy.context.scene.collection.objects.link(obj)

    modifier = obj.modifiers.new(name="Terrain", type="NODES")
    modifier.node_group = group

    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    return obj


def report(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    verts = len(mesh.vertices)
    faces = len(mesh.polygons)
    evaluated.to_mesh_clear()

    print("-" * 56)
    print("Blender %s" % bpy.app.version_string)
    print("Built %r driven by node group %r" % (obj.name, NODE_GROUP_NAME))
    print("Vertices: %d   Faces: %d   (~%d triangles)" % (verts, faces, faces * 2))
    print("Adjust values on the Terrain modifier in Properties > Modifiers.")
    print("-" * 56)


def main():
    clear_previous()
    group = build_node_group()
    obj = build_object(group)
    report(obj)


if __name__ == "__main__":
    main()
