from meshcad.core.boundary import PatchModel
from meshcad.core.cfd import CfdCell,CfdFace,CfdMesh
from meshcad.core.geometry.point import Point2D
from meshcad.io.cfd_mesh_io import cfd_mesh_to_dict

def test_export_contains_patch_ids_but_no_solver_bc_types():
    patches=PatchModel(); patch=patches.add_patch("outer")
    nodes=tuple(Point2D(*p) for p in ((0,0),(1,0),(1,1),(0,1)))
    cell=CfdCell(0,(0,1,2,3),0,0,0,1.0)
    faces=tuple(CfdFace(i,e,0,patch_id=patch.id) for i,e in enumerate(((0,1),(1,2),(2,3),(3,0))))
    data=cfd_mesh_to_dict(CfdMesh(nodes,(cell,),faces),patches)
    assert data["format"]=="meshcad-mesh"
    assert data["faces"]["patch"]==[0,0,0,0]
    assert data["patches"]==[{"id":0,"name":"outer","faces":[0,1,2,3]}]
    assert "periodic_pairs" not in data
