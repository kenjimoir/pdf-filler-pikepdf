# PDF Filler Service

A modern PDF form filler service with excellent Japanese text support, using **pikepdf** (recommended) or PDFtk (legacy).

## 🚀 New: pikepdf Support

We now support **pikepdf** - a modern Python library that provides:
- ✅ **Superior Unicode support** - Handles Japanese characters flawlessly
- ✅ **Better appearance handling** - Automatically regenerates /AP (Appearance) dictionaries
- ✅ **Active maintenance** - Built on QPDF, regularly updated
- ✅ **Font preservation** - Better font handling than PDFtk's older iText2.x foundation

### Why pikepdf over PDFtk?

PDFtk is based on iText2.x (released 2008), which has limitations:
- ❌ AcroForm update processing is lax
- ❌ Appearance dictionaries (/AP) may not be properly regenerated
- ❌ Font encoding issues with complex Unicode

**pikepdf** solves these issues by using modern PDF libraries under the hood.

## Prerequisites

### For pikepdf (Recommended)

The Docker image includes Python 3 and pikepdf automatically.

**Local development:**
```bash
pip3 install pikepdf
```

### For PDFtk (Legacy)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install pdftk
```

**macOS:**
```bash
brew install pdftk-java
```

**Alternative:**
```bash
sudo apt-get install pdftk-java
```

### Verify Installation

```bash
# Check pikepdf
python3 -c "import pikepdf; print(pikepdf.__version__)"

# Check PDFtk (legacy)
pdftk --version
```

## Environment Variables

Set these in your deployment environment (e.g., Railway, Render):

### Required
- `GOOGLE_CREDENTIALS_JSON` - Google service account credentials (JSON string)
- `GOOGLE_APPLICATION_CREDENTIALS` - Alternative: Path to Google credentials file
- `OUTPUT_FOLDER_ID` - Google Drive folder ID for output files (optional)

### Optional
- `PORT` - Server port (default: 8080)
- `PDF_FILL_METHOD` - Set to `'pikepdf'` (default) or `'pdftk'` for legacy mode

**Example (Railway/Render):**
```
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
PDF_FILL_METHOD=pikepdf
OUTPUT_FOLDER_ID=1abc...
PORT=8080
```

## Usage

### Health Check
```bash
GET /health
```

Returns:
```json
{
  "ok": true,
  "pdftkAvailable": true,
  "pikepdfAvailable": true,
  "preferredMethod": "pikepdf",
  "outputFolder": "1abc...",
  "tempDir": "/tmp/pdf-filler-pdftk"
}
```

### Fill PDF
```bash
POST /fill
```

Request body:
```json
{
  "templateFileId": "1bcKCkuGuu3tilqw-Uu7S5g2bIH6hfLoN",
  "fields": {
    "ApplicantName": "モイア 憲史",
    "ApplicantAddress": "東京都世田谷区池尻 5-55-5",
    "Age": "28",
    "TreatmentNow": "no",
    "SeriousHistory": "yes"
  },
  "outputName": "保険申込書_12345.pdf",
  "folderId": "1t9xr8xNJDnVahtAhiyMwPCqyLKavLxsH",
  "mode": "final",
  "flattenMethod": "none"
}
```

Response:
```json
{
  "ok": true,
  "driveFile": {
    "id": "1abc...",
    "name": "保険申込書_12345.pdf",
    "webViewLink": "https://drive.google.com/...",
    "webContentLink": "https://drive.google.com/..."
  },
  "method": "pikepdf"
}
```

## How It Works

### With pikepdf (Default)

1. **Download template** from Google Drive
2. **Parse PDF** with pikepdf (modern PDF library)
3. **Fill form fields** with proper Unicode encoding (UTF-16BE for Japanese)
4. **Check and regenerate appearances** - Automatically fixes missing /AP dictionaries
5. **Upload result** to Google Drive
6. **Cleanup** temporary files

### With PDFtk (Legacy)

1. **Download template** from Google Drive
2. **Generate FDF** (Form Data Format) from field data
3. **Use PDFtk** to fill form
4. **Post-process** with PDFBox to refresh appearances
5. **Upload result** to Google Drive
6. **Cleanup** temporary files

## Key Features

### pikepdf Advantages

- ✅ **Automatic appearance regeneration** - Detects and fixes missing /AP dictionaries
- ✅ **Better font handling** - Preserves fonts correctly
- ✅ **UTF-16BE encoding** - Proper Japanese text encoding
- ✅ **Form field detection** - Recursively finds all fields including nested ones
- ✅ **Checkbox/Radio button support** - Handles export values correctly

### Request Options

- `mode`: `'final'` (default), `'preview'`, `'copy'`, `'pdftk-copy'`
- `flattenMethod`: `'none'` (default - keeps form editable), or `'gs'` for Ghostscript flattening

**Example (keep form editable):**
```json
{
  "templateFileId": "...",
  "fields": {...},
  "mode": "final",
  "flattenMethod": "none"
}
```

## Migration from PDFtk

The service defaults to **pikepdf**. No code changes needed!

To use PDFtk (legacy mode), set environment variable:
```
PDF_FILL_METHOD=pdftk
```

## Deployment

### Railway / Render.com

1. Connect your GitHub repository
2. Set build command: `npm install` (or let Docker build handle it)
3. Set start command: `npm start`
4. Add environment variables (see above)
5. **Important**: Set `PDF_FILL_METHOD=pikepdf` (or leave unset for default)
6. Deploy!

### Docker

```bash
docker build -t pdf-filler .
docker run -p 8080:8080 \
  -e GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}' \
  -e PDF_FILL_METHOD=pikepdf \
  pdf-filler
```

### Local Development

```bash
# Install dependencies
npm install

# Install Python dependencies (for pikepdf)
pip3 install pikepdf

# Set environment variables
export GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
export PDF_FILL_METHOD=pikepdf

# Start server
npm start
```

## Troubleshooting

### pikepdf not found
- Check Python 3 is installed: `python3 --version`
- Install pikepdf: `pip3 install pikepdf`
- Verify: `python3 -c "import pikepdf; print(pikepdf.__version__)"`

### PDFtk not found (legacy mode)
- Install PDFtk on your system
- Check with `pdftk --version`
- Try alternative installation methods

### Google Drive errors
- Verify service account has access to template and output folder
- Check credentials are properly set
- Ensure folder IDs are correct

### Appearance issues (fonts not showing)
- **With pikepdf**: Appearance regeneration should happen automatically
- **With PDFtk**: Try switching to pikepdf mode
- Check that PDF template has proper font embedding

### Field not filling
- Check field names match PDF template exactly (case-sensitive)
- Verify field type (text vs checkbox vs radio)
- Check logs for skipped fields

## Architecture

- **Node.js/Express** - HTTP API server
- **pikepdf (Python)** - PDF manipulation (default, recommended)
- **PDFtk** - Legacy PDF tool (fallback)
- **Google Drive API** - Template download and result upload

## License

MIT
