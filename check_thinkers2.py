"""문맥 0건인 이론가의 XML 마크업 패턴 진단"""
import json, glob
from xml.etree import ElementTree as ET

TEI_NS = "http://www.w3.org/XML/1998/namespace"
T = "http://www.tei-c.org/ns/1.0"

def tns(tag):
    return f"{{{T}}}{tag}"

def get_attr_id(elem):
    return elem.get(f"{{{TEI_NS}}}id", "")

data = json.loads(open("site/data/thinkers.json", encoding="utf-8").read())
zero_ctx = [t for t in data if t["context_count"] == 0]

print(f"문맥 0건 이론가: {len(zero_ctx)}명\n")

for t in zero_ctx:
    tid = t["id"]
    name = t["name"]
    print(f"=== {name} ({tid}) ===")
    for fpath in sorted(glob.glob("essays/*.xml")):
        tree = ET.parse(fpath)
        root = tree.getroot()
        hits = []
        for pn in root.iter(tns("persName")):
            xml_id = get_attr_id(pn)
            ref = pn.get("ref", "")
            pid = xml_id if xml_id else (ref[1:] if ref.startswith("#") else "")
            if pid == tid:
                role = pn.get("role", "")
                parent_tag = ""
                # 부모 찾기 간이
                text_snippet = "".join(pn.itertext()).strip()[:40]
                hits.append(f"  role='{role}' text='{text_snippet}'")
        if hits:
            import os
            print(f"  [{os.path.basename(fpath)}]")
            for h in hits:
                print(h)
    print()
