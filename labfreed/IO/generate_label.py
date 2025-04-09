import os

from .generate_qr import generate_qr_with_markers_svg

from labfreed.PAC_ID.data_model import  PACID
from labfreed.DisplayNameExtension.DisplayNameExtension import DisplayNames
from labfreed.IO.parse_pac import PACID_With_Extensions


    

    
def generate_label_200_100(pac_url, pac:PACID_With_Extensions):
    title, infos = get_label_fields(pac)
    pac_svg = generate_qr_with_markers_svg(pac_url, height=60, width=100, border=0)
    label = _generate_label(pac_svg, 200, 100, title, infos)
    return label

def generate_label_credit_card_size(pac_url, pac:PACID_With_Extensions):
    title, infos = get_label_fields(pac)
    pac_svg = generate_qr_with_markers_svg(pac_url, height=100, width=200, border=0)
    label = _generate_label(pac_svg, 240, 150, title, infos)
    return label
    
    
def _generate_label(qr_svg, width, height, title=None, infos=[]):
    if not qr_svg:
        raise ValueError("no valid qr given")
    env = Environment(
		loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
		autoescape=select_autoescape()
	)
    template = env.get_template("pac_label.jinja.svg")
    svg = template.render(width=width, height= height, pac_qr=qr_svg, title=title, info1=infos[0], info2=infos[1], info3=infos[2])
    
    return svg



def get_label_fields(pac:PACID_With_Extensions) -> tuple[str, list[tuple[str, str]]]:
    '''
    returns a list of exactly length 3. Containing either info tuples (key value) or None
    '''
    if dn_extension := next((e for e in pac.extensions if isinstance(e, DisplayNames)), None): #find extension of type DisplayName
        title = dn_extension.display_names[0]
    else:
        title = ""
    
    infos = []
    cat = pac.pac_id.identifier.categories[0]
    for s in cat.segments:
        lbl = pretty_print_segment_label(cat.key, s.key)
        infos.append((lbl, s.value))
        
    while len(infos) < 3:
        infos.append(None)
    
    if len(infos) > 3:
        infos = infos[0:3]
           
    return title,infos


def pretty_print_segment_label(category:str, segment_key:str):
    if not segment_key:
        return 'no key'
    
    cat = CAT_from_category_key(category)
    if cat:
        alias_to_field = {v.alias: k for k, v in cat.model_fields.items() if v.alias}
        segment_label = alias_to_field.get(segment_key, segment_key)
        segment_label = segment_label.replace('_', ' ').title()
        
        segment_label = segment_label.replace('Id', 'ID')
        
    else:
        segment_label = segment_key
    
    return segment_label
    
    