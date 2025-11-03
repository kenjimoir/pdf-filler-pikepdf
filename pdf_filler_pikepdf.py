#!/usr/bin/env python3
"""
PDF Filler using pikepdf - Modern, robust PDF manipulation with excellent Unicode support
Handles form filling, appearance regeneration, and font preservation for Japanese text
"""

import sys
import json
import argparse
from pathlib import Path
import pikepdf
from pikepdf import Pdf, Object, Name, String, Dictionary, Array


def utf16_hex_encode(text):
    """Encode text as UTF-16BE hex string for PDF form fields"""
    if not text:
        return String('')
    try:
        # PDF uses UTF-16BE (Big-Endian) with BOM
        encoded = text.encode('utf-16be')
        # Add BOM: FE FF
        bom = b'\xfe\xff'
        full_bytes = bom + encoded
        # Convert to hex string and uppercase
        hex_str = full_bytes.hex().upper()
        # Return as PDF hex string
        return String(f'<{hex_str}>')
    except Exception as e:
        # Fallback to plain text if encoding fails
        print(f"⚠️  UTF-16 encoding failed for '{text[:20]}...': {e}, using plain text")
        return String(text)


def ensure_pdf_name(value):
    """Ensure a value is a valid PDF Name object (must start with '/')"""
    if not value:
        return Name('/Off')
    value_str = str(value).strip()
    # Remove leading '/' if present, then add it back to ensure consistency
    value_str = value_str.lstrip('/')
    # PDF Name objects must start with '/'
    return Name('/' + value_str)


def create_checkbox_appearance(pdf, rect_array, state_name):
    """Create appearance stream for checkbox field"""
    try:
        # Ensure rect_array is a list/array with at least 4 elements
        if not rect_array or len(rect_array) < 4:
            return None
        
        # Extract rectangle coordinates (handle Object references)
        def get_float_value(val):
            if isinstance(val, Object):
                try:
                    # Try to convert Object to float directly
                    return float(val)
                except (TypeError, ValueError):
                    try:
                        # Try string conversion
                        return float(str(val))
                    except (TypeError, ValueError):
                        return 0.0
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0
        
        x0 = get_float_value(rect_array[0])
        y0 = get_float_value(rect_array[1])
        x1 = get_float_value(rect_array[2])
        y1 = get_float_value(rect_array[3])
        
        width = x1 - x0
        height = y1 - y0
        
        # Ensure we have valid dimensions
        if width <= 0 or height <= 0:
            return None
        
        # Create appearance stream
        # Simple checkbox appearance: border + checkmark if checked
        if state_name == Name('/Off'):
            # Unchecked: just border
            stream_content = f"""q
0.0 0.0 0.0 rg
{width} 0 0 {height} 0 0 cm
0.5 w
0 0 m
{width} 0 l
{width} {height} l
0 {height} l
0 0 l
S
Q
"""
        else:
            # Checked: border + checkmark
            # Draw checkmark using simple lines
            check_size = min(width, height) * 0.6
            check_x = width * 0.3
            check_y = height * 0.5
            check_thickness = min(width, height) * 0.15
            
            stream_content = f"""q
0.0 0.0 0.0 rg
{width} 0 0 {height} 0 0 cm
0.5 w
0 0 m
{width} 0 l
{width} {height} l
0 {height} l
0 0 l
S
{check_thickness} w
{check_x} {check_y} m
{check_x - check_size*0.3} {check_y - check_size*0.2} l
{check_x + check_size*0.3} {check_y + check_size*0.2} l
S
{check_x} {check_y} m
{check_x + check_size*0.3} {check_y + check_size*0.2} l
S
Q
"""
        
        # Create appearance dictionary
        appearance_stream = pdf.make_stream(stream_content.encode('latin-1'))
        appearance_dict = Dictionary({
            Name('/N'): appearance_stream  # Normal appearance
        })
        
        return appearance_dict
        
    except Exception as e:
        print(f"⚠️  Error creating checkbox appearance: {e}")
        return None


def create_radio_appearance(pdf, rect_array, state_name):
    """Create appearance stream for radio button field"""
    try:
        # Ensure rect_array is a list/array with at least 4 elements
        if not rect_array or len(rect_array) < 4:
            return None
        
        # Extract rectangle coordinates (handle Object references)
        def get_float_value(val):
            if isinstance(val, Object):
                try:
                    # Try to convert Object to float directly
                    return float(val)
                except (TypeError, ValueError):
                    try:
                        # Try string conversion
                        return float(str(val))
                    except (TypeError, ValueError):
                        return 0.0
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0
        
        x0 = get_float_value(rect_array[0])
        y0 = get_float_value(rect_array[1])
        x1 = get_float_value(rect_array[2])
        y1 = get_float_value(rect_array[3])
        
        width = x1 - x0
        height = y1 - y0
        
        # Ensure we have valid dimensions
        if width <= 0 or height <= 0:
            return None
        
        # Calculate center and radius
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 2
        
        # Create appearance stream
        if state_name == Name('/Off'):
            # Unchecked: just circle border
            stream_content = f"""q
0.0 0.0 0.0 rg
{width} 0 0 {height} 0 0 cm
0.5 w
{center_x} {center_y} {radius} 0 360 arc
S
Q
"""
        else:
            # Checked: circle border + filled center
            inner_radius = radius * 0.6
            stream_content = f"""q
0.0 0.0 0.0 rg
{width} 0 0 {height} 0 0 cm
0.5 w
{center_x} {center_y} {radius} 0 360 arc
S
0.5 g
{center_x} {center_y} {inner_radius} 0 360 arc
f
Q
"""
        
        # Create appearance dictionary
        appearance_stream = pdf.make_stream(stream_content.encode('latin-1'))
        appearance_dict = Dictionary({
            Name('/N'): appearance_stream  # Normal appearance
        })
        
        return appearance_dict
        
    except Exception as e:
        print(f"⚠️  Error creating radio appearance: {e}")
        return None


def check_and_fix_appearances(pdf):
    """
    Check for missing /AP (Appearance) dictionaries in form fields
    and regenerate them if needed.
    Returns tuple: (needs_fix, fixed_count)
    """
    try:
        if not pdf.Root.get('/AcroForm'):
            return False, 0
        
        acro_form = pdf.Root.AcroForm
        if not acro_form:
            return False, 0
        
        fields = acro_form.get('/Fields', [])
        if not fields:
            return False, 0
        
        needs_fix = False
        fixed_count = 0
        
        # Traverse all fields recursively
        def check_field(field_ref):
            nonlocal needs_fix, fixed_count
            field = field_ref
            
            # Check if this is a terminal field (not a parent)
            field_type = field.get('/FT')
            if field_type:  # Field Type exists
                # Check for missing /AP (Appearance)
                if '/AP' not in field:
                    field_name = field.get('/T', 'unknown')
                    if isinstance(field_name, String):
                        field_name = str(field_name)
                    needs_fix = True
                    print(f"⚠️  Field missing /AP: {field_name}")
                    
                    # For buttons (checkboxes/radio), we need to regenerate appearance
                    if field_type == Name('/Btn'):
                        # Try to regenerate appearance by setting NeedAppearances flag
                        needs_fix = True
                        fixed_count += 1
            
            # Check children (for non-terminal fields)
            kids = field.get('/Kids', [])
            for kid in kids:
                if isinstance(kid, Object):
                    check_field(kid)
        
        # Process all root-level fields
        for field_ref in fields:
            if isinstance(field_ref, Object):
                check_field(field_ref)
        
        return needs_fix, fixed_count
        
    except Exception as e:
        print(f"⚠️  Error checking appearances: {e}")
        return False, 0


def fill_pdf_with_pikepdf(template_path, output_path, fields, options=None):
    """
    Fill PDF form fields using pikepdf
    
    Args:
        template_path: Path to template PDF
        output_path: Path to output PDF
        fields: Dictionary of field_name -> value
        options: Dictionary with options like:
            - regenerate_appearances: bool (default: True)
            - flatten: bool (default: False)
    
    Returns:
        Dictionary with success status and metadata
    """
    if options is None:
        options = {}
    
    regenerate_appearances = options.get('regenerate_appearances', True)
    flatten = options.get('flatten', False)
    
    print(f"📝 Opening template: {template_path}")
    pdf = Pdf.open(template_path)
    
    # Check for AcroForm
    if not pdf.Root.get('/AcroForm'):
        print("⚠️  Template PDF has no AcroForm. Cannot fill fields.")
        pdf.save(output_path)
        return {'success': False, 'error': 'No AcroForm found'}
    
    acro_form = pdf.Root.AcroForm
    form_fields = {}
    
    # Collect all field names (with recursion for nested fields)
    def collect_fields(field_ref, prefix=''):
        field = field_ref
        field_type = field.get('/FT')
        field_name_raw = field.get('/T')
        
        # Convert field name to string (handle String objects and Object references)
        field_name = None
        if field_name_raw:
            if isinstance(field_name_raw, String):
                field_name = str(field_name_raw)
            elif hasattr(field_name_raw, '__str__'):
                field_name = str(field_name_raw)
            else:
                field_name = None
        
        if field_type and field_name:
            full_name = f"{prefix}.{field_name}" if prefix else field_name
            form_fields[full_name] = field_ref
        
        # Check children
        kids = field.get('/Kids', [])
        for kid in kids:
            if isinstance(kid, Object):
                new_prefix = f"{prefix}.{field_name}" if prefix else (field_name or '')
                if new_prefix:
                    collect_fields(kid, new_prefix)
    
    # Collect all form fields
    fields_array = acro_form.get('/Fields', [])
    for field_ref in fields_array:
        if isinstance(field_ref, Object):
            collect_fields(field_ref)
    
    print(f"📋 Found {len(form_fields)} form fields")
    
    # Check for missing appearances before filling
    if regenerate_appearances:
        needs_fix, count = check_and_fix_appearances(pdf)
        if needs_fix:
            print(f"⚠️  Found {count} fields with missing /AP")
    
    # Fill fields
    filled_count = 0
    skipped_count = 0
    
    for field_name, value in fields.items():
        if value is None or value == '':
            continue
        
        # Try exact match first
        field_ref = form_fields.get(field_name)
        
        if not field_ref:
            # Try case-insensitive match
            field_name_lower = field_name.lower()
            for name, ref in form_fields.items():
                # Ensure name is a string before calling .lower()
                name_str = str(name) if name else ''
                if name_str.lower() == field_name_lower:
                    field_ref = ref
                    break
        
        if not field_ref:
            skipped_count += 1
            continue
        
        try:
            field = field_ref
            field_type = field.get('/FT')
            
            if not field_type:
                skipped_count += 1
                continue
            
            if field_type == Name('/Tx'):  # Text field
                # Use plain String object - pikepdf and PDF viewers handle encoding automatically
                # This is more reliable than manual UTF-16BE hex encoding
                if isinstance(value, str):
                    field_value = String(value)
                else:
                    field_value = String(str(value))
                field['/V'] = field_value
                # Clear /I (inline) if present to force appearance regeneration
                if '/I' in field:
                    del field['/I']
                # Remove /AP to force regeneration (will be regenerated by PDF viewer)
                if '/AP' in field:
                    del field['/AP']
                filled_count += 1
                
            elif field_type == Name('/Btn'):  # Button (checkbox/radio)
                button_type = int(field.get('/Ff', 0) or 0)
                is_checkbox = (button_type & 0x8000) == 0  # Not radio button flag
                
                value_str = str(value).lower()
                
                state_name = None
                if is_checkbox:
                    # Checkbox
                    if value_str in ('on', 'true', '1', 'yes'):
                        # Get the on-state name (export value)
                        opt = field.get('/Opt')
                        on_value = 'Yes'
                        if opt:
                            if isinstance(opt, Array) and len(opt) > 0:
                                opt_val = opt[0]
                                if isinstance(opt_val, String):
                                    on_value = str(opt_val)
                                elif isinstance(opt_val, Array) and len(opt_val) > 0:
                                    on_value = str(opt_val[0])
                        # Ensure Name object starts with '/'
                        state_name = ensure_pdf_name(on_value)
                        field['/V'] = state_name
                        field['/AS'] = state_name
                    else:
                        state_name = ensure_pdf_name('Off')
                        field['/V'] = state_name
                        field['/AS'] = state_name
                else:
                    # Radio button - value should match export value (convert to name)
                    # Use value as-is but ensure it's a Name object starting with '/'
                    export_value = value_str
                    state_name = ensure_pdf_name(export_value)
                    field['/V'] = state_name
                    field['/AS'] = state_name
                
                # Create appearance stream for button fields
                # Get Rect from field's Kids (annotations) or from pages
                rect_array = None
                
                # Method 1: Try to get Rect from field's Kids (annotations)
                kids = field.get('/Kids', [])
                if kids and len(kids) > 0:
                    for kid in kids:
                        if isinstance(kid, Object):
                            try:
                                kid_dict = kid if isinstance(kid, Dictionary) else kid
                                kid_rect = kid_dict.get('/Rect')
                                if kid_rect:
                                    # Convert to list if it's an Object reference
                                    if isinstance(kid_rect, Array):
                                        rect_array = kid_rect
                                    elif hasattr(kid_rect, '__iter__'):
                                        rect_array = list(kid_rect)
                                    if rect_array and len(rect_array) >= 4:
                                        break
                            except Exception:
                                continue
                
                # Method 2: Try to get Rect from pages (search for annotation with matching field name)
                if not rect_array:
                    field_name_raw = field.get('/T')
                    field_name_str = str(field_name_raw) if field_name_raw else None
                    if field_name_str:
                        for page in pdf.pages:
                            annots = page.get('/Annots', [])
                            if not annots:
                                continue
                            for annot in annots:
                                if isinstance(annot, Object):
                                    try:
                                        annot_dict = annot if isinstance(annot, Dictionary) else annot
                                        annot_field_name = annot_dict.get('/T')
                                        if annot_field_name and str(annot_field_name) == field_name_str:
                                            annot_rect = annot_dict.get('/Rect')
                                            if annot_rect:
                                                if isinstance(annot_rect, Array):
                                                    rect_array = annot_rect
                                                elif hasattr(annot_rect, '__iter__'):
                                                    rect_array = list(annot_rect)
                                                if rect_array and len(rect_array) >= 4:
                                                    break
                                    except Exception:
                                        continue
                            if rect_array:
                                break
                
                # If we have Rect, create appearance
                if rect_array and len(rect_array) >= 4:
                    try:
                        if is_checkbox:
                            appearance = create_checkbox_appearance(pdf, rect_array, state_name)
                        else:
                            appearance = create_radio_appearance(pdf, rect_array, state_name)
                        
                        if appearance:
                            field['/AP'] = appearance
                            print(f"✅ Created appearance for {field_name}")
                    except Exception as e:
                        print(f"⚠️  Could not create appearance for {field_name}: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    # No Rect available, remove /AP to let viewer regenerate
                    if '/AP' in field:
                        del field['/AP']
                
                filled_count += 1
                
            else:
                # Other field types - try to set value
                field['/V'] = String(str(value))
                filled_count += 1
                
        except Exception as e:
            print(f"⚠️  Error filling field '{field_name}': {e}")
            import traceback
            traceback.print_exc()
            skipped_count += 1
            continue
    
    print(f"✅ Filled {filled_count} fields (skipped {skipped_count})")
    
    # Regenerate appearances if needed
    if regenerate_appearances:
        print("🔄 Setting NeedAppearances flag...")
        acro_form['/NeedAppearances'] = True
        
        # Also check and fix appearances after filling
        needs_fix, count = check_and_fix_appearances(pdf)
        if needs_fix or count > 0:
            print(f"⚠️  After filling: {count} fields may need appearance regeneration")
    
    # Flatten if requested
    if flatten:
        print("📄 Flattening form (making non-editable)...")
        pdf.Root.AcroForm = None  # Remove AcroForm to flatten
    else:
        # Keep form editable but ensure appearances are visible
        acro_form['/NeedAppearances'] = True
    
    # Save output
    print(f"💾 Saving to: {output_path}")
    pdf.save(output_path, compress_streams=True)
    pdf.close()
    
    output_size = Path(output_path).stat().st_size
    print(f"✅ PDF created successfully ({output_size} bytes)")
    
    return {
        'success': True,
        'filled_count': filled_count,
        'skipped_count': skipped_count,
        'total_fields': len(form_fields),
        'output_size': output_size
    }


def main():
    parser = argparse.ArgumentParser(description='Fill PDF form using pikepdf')
    parser.add_argument('template_path', help='Path to template PDF')
    parser.add_argument('output_path', help='Path to output PDF')
    parser.add_argument('--fields', required=True, help='JSON string of field_name:value pairs')
    parser.add_argument('--regenerate-appearances', action='store_true', default=True,
                        help='Regenerate appearances for form fields')
    parser.add_argument('--no-regenerate-appearances', dest='regenerate_appearances', action='store_false',
                        help='Do not regenerate appearances')
    parser.add_argument('--flatten', action='store_true', default=False,
                        help='Flatten PDF (remove form fields)')
    
    args = parser.parse_args()
    
    # Parse fields JSON
    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing fields JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Fill PDF
    options = {
        'regenerate_appearances': args.regenerate_appearances,
        'flatten': args.flatten
    }
    
    try:
        result = fill_pdf_with_pikepdf(args.template_path, args.output_path, fields, options)
        
        # Output result as JSON
        print(json.dumps(result))
        
        if not result.get('success'):
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

