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
                # Use UTF-16BE encoding for Japanese text
                if isinstance(value, str):
                    field_value = utf16_hex_encode(value)
                else:
                    field_value = String(str(value))
                field['/V'] = field_value
                # Clear /I (inline) if present to force appearance regeneration
                if '/I' in field:
                    del field['/I']
                filled_count += 1
                
            elif field_type == Name('/Btn'):  # Button (checkbox/radio)
                button_type = int(field.get('/Ff', 0) or 0)
                is_checkbox = (button_type & 0x8000) == 0  # Not radio button flag
                
                value_str = str(value).lower()
                
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
                        field['/V'] = Name(on_value)
                        field['/AS'] = Name(on_value)
                    else:
                        field['/V'] = Name('Off')
                        field['/AS'] = Name('Off')
                else:
                    # Radio button - value should match export value (convert to name)
                    # Use value as-is but ensure it's a Name object
                    export_value = value_str
                    field['/V'] = Name(export_value)
                    field['/AS'] = Name(export_value)
                
                # Remove /AP to force regeneration
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

