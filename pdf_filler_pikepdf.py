#!/usr/bin/env python3
"""
PDF Filler using pikepdf - Set values only, preserve template fonts and appearances
This script sets /V and /AS without updating appearances, letting PDF viewer handle display
"""

import sys
import json
import argparse
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Name, String

def str_to_bool(v):
    """Convert value to boolean"""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    v_str = str(v).strip().lower()
    return v_str in {"1", "true", "on", "yes", "y", "t"}

def is_radio(field_dict):
    """Check if field is a radio button"""
    ff = int(field_dict.get("/Ff", 0) or 0)
    return (ff & 0x8000) != 0

def collect_fields(root_fields):
    """Build a map of full field name -> field dict"""
    result = {}
    
    def walk(field, prefix=""):
        fname_obj = field.get("/T")
        fname = str(fname_obj) if fname_obj is not None else None
        ft = field.get("/FT")
        full = f"{prefix}.{fname}" if prefix and fname else (fname or prefix)
        
        kids = field.get("/Kids")
        if ft is not None:
            if full:
                result[full] = field
        
        if kids:
            next_prefix = full or prefix
            for kid in kids:
                walk(kid, next_prefix)
    
    for f in root_fields:
        walk(f, "")
    
    return result

def widgets_for_field(pdf: Pdf, field: dict):
    """Find widget annotations belonging to a field"""
    widgets = []
    
    for page in pdf.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        
        for annot in annots:
            try:
                if annot.get("/Subtype") != Name("/Widget"):
                    continue
                parent = annot.get("/Parent")
                if parent is field:
                    widgets.append(annot)
            except Exception:
                continue
    
    if not widgets:
        kids = field.get("/Kids")
        if kids:
            for kid in kids:
                try:
                    if kid.get("/Subtype") == Name("/Widget"):
                        widgets.append(kid)
                except Exception:
                    continue
    
    return widgets

def fill_pdf(template_path: str, output_path: str, fields: dict, list_fields: bool = False):
    """Fill PDF form fields - set values only, preserve template appearances"""
    pdf = Pdf.open(template_path)
    
    acro = pdf.Root.get("/AcroForm")
    if not acro:
        pdf.save(output_path)
        pdf.close()
        return {'success': False, 'error': 'No AcroForm found'}
    
    root_fields = acro.get("/Fields", [])
    field_map = collect_fields(root_fields)
    
    if list_fields:
        field_names = list(field_map.keys())
        pdf.close()
        return {'success': True, 'field_names': field_names}
    
    filled = 0
    skipped = []
    
    # DO NOT set /NeedAppearances or update appearances
    # Just set /V and /AS, let PDF viewer handle display
    
    for raw_name, value in fields.items():
        if value is None or value == '':
            continue
        
        field_name = raw_name
        field_dict = field_map.get(field_name)
        
        if not field_dict:
            low = field_name.lower()
            for k, v in field_map.items():
                if str(k).lower() == low:
                    field_name, field_dict = k, v
                    break
        
        if not field_dict:
            skipped.append(raw_name)
            continue
        
        ft = field_dict.get("/FT")
        
        if ft == Name("/Tx"):
            # Text field: set /V only, preserve template appearance/fonts
            field_dict["/V"] = String("" if value is None else str(value))
            filled += 1
            continue
        
        if ft == Name("/Btn"):
            widgets = widgets_for_field(pdf, field_dict)
            
            if not widgets:
                skipped.append(raw_name)
                continue
            
            if is_radio(field_dict):
                # Radio: find widget with matching export value
                value_str = str(value).strip().lower().lstrip("/")
                found_widget = None
                found_name = None
                
                for w in widgets:
                    ap = w.get("/AP")
                    if not ap:
                        continue
                    apN = ap.get("/N")
                    if not apN:
                        continue
                    try:
                        keys = list(apN.keys())
                        for k in keys:
                            if str(k)[1:].lower() == value_str:
                                found_widget = w
                                found_name = k
                                break
                        if found_widget:
                            break
                    except Exception:
                        continue
                
                if found_widget and found_name:
                    field_dict["/V"] = found_name
                    for ww in widgets:
                        ww["/AS"] = found_name if ww is found_widget else Name("/Off")
                    filled += 1
                else:
                    skipped.append(raw_name)
                continue
            
            # Checkbox: use /Yes or /Off based on value
            on_state = Name("/Yes")
            off_state = Name("/Off")
            
            if str_to_bool(value):
                field_dict["/V"] = on_state
                for ww in widgets:
                    ww["/AS"] = on_state
            else:
                field_dict["/V"] = off_state
                for ww in widgets:
                    ww["/AS"] = off_state
            
            filled += 1
            continue
        
        # Other field types
        field_dict["/V"] = String("" if value is None else str(value))
        filled += 1
    
    pdf.save(output_path, compress_streams=True)
    pdf.close()
    
    output_size = Path(output_path).stat().st_size
    
    return {
        'success': True,
        'filled_count': filled,
        'skipped_count': len(skipped),
        'skipped_fields': skipped,
        'total_fields': len(field_map),
        'output_size': output_size
    }

def main():
    parser = argparse.ArgumentParser(description='Fill PDF form using pikepdf - set values only')
    parser.add_argument('template_path', help='Path to template PDF')
    parser.add_argument('output_path', help='Path to output PDF')
    parser.add_argument('--fields', required=True, help='JSON string of field_name:value pairs')
    parser.add_argument('--list-fields', action='store_true', help='List field names and exit')
    
    args = parser.parse_args()
    
    if args.list_fields:
        result = fill_pdf(args.template_path, args.output_path, {}, list_fields=True)
        print(json.dumps(result))
        sys.exit(0 if result.get('success') else 1)
    
    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing fields JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"📝 Opening template: {args.template_path}")
    
    try:
        result = fill_pdf(args.template_path, args.output_path, fields)
        
        if result.get('success'):
            print(f"✅ Filled {result['filled_count']} fields (skipped {result['skipped_count']})")
            print(f"💾 Saving to: {args.output_path}")
            print(f"✅ PDF created successfully ({result['output_size']} bytes)")
            print(json.dumps(result))
            sys.exit(0)
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

