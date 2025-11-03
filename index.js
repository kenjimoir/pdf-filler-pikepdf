// PDF Filler using pdf-lib - Reliable Japanese text support with automatic appearance updates
// Based on school application form approach - proven to work without appearance issues

const fs = require('fs');
const os = require('os');
const path = require('path');
const express = require('express');
const cors = require('cors');
const { PDFDocument } = require('pdf-lib');
const { google } = require('googleapis');

const PORT = process.env.PORT || 8080;
const TMP = path.join(os.tmpdir(), 'pdf-filler-pdflib');
const OUTPUT_FOLDER_ID = process.env.OUTPUT_FOLDER_ID || '';

// Ensure temp directory exists
function ensureDir(p) {
  if (!fs.existsSync(p)) {
    fs.mkdirSync(p, { recursive: true });
  }
}
ensureDir(TMP);

function log(...args) {
  console.log(new Date().toISOString(), '-', ...args);
}

// ---- Google Drive client (supports Shared Drives) ----
function getDriveClient() {
  // Option A: GOOGLE_CREDENTIALS_JSON (paste JSON into Render env var)
  // Option B: GOOGLE_APPLICATION_CREDENTIALS (path to a mounted JSON file)
  let credentials = null;
  
  if (process.env.GOOGLE_CREDENTIALS_JSON) {
    try {
      credentials = JSON.parse(process.env.GOOGLE_CREDENTIALS_JSON);
    } catch (e) {
      log('ERROR parsing GOOGLE_CREDENTIALS_JSON:', e && e.message);
      throw new Error(`Invalid GOOGLE_CREDENTIALS_JSON: ${e.message}`);
    }
  }
  
  const auth = new google.auth.GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/drive'],
    ...(credentials ? { credentials } : {}) // fallback to ADC / GOOGLE_APPLICATION_CREDENTIALS
  });
  
  return google.drive({ version: 'v3', auth });
}

// ---- Drive helpers ----
async function downloadDriveFile(fileId, destPath) {
  const drive = getDriveClient();
  log('📥 Downloading template', fileId, '→', destPath);
  
  // First check file metadata to see if it's a Google Doc
  const meta = await drive.files.get({
    fileId,
    fields: 'id, name, mimeType',
    supportsAllDrives: true,
  });
  
  if (meta.data.mimeType && meta.data.mimeType.startsWith('application/vnd.google-apps')) {
    // Google Doc - export as PDF
    const res = await drive.files.export(
      { fileId, mimeType: 'application/pdf' },
      { responseType: 'stream' }
    );
    await new Promise((resolve, reject) => {
      const out = fs.createWriteStream(destPath);
      res.data.on('error', reject).pipe(out).on('finish', resolve);
    });
  } else {
    // Binary PDF file
    const res = await drive.files.get(
      { fileId, alt: 'media', supportsAllDrives: true },
      { responseType: 'stream' }
    );
    await new Promise((resolve, reject) => {
      const out = fs.createWriteStream(destPath);
      res.data.on('error', reject).pipe(out).on('finish', resolve);
    });
  }
  
  return destPath;
}

async function uploadToDrive(localPath, name, parentId) {
  /**
   * Upload localPath to Drive.
   * - If parentId is provided (from request), it is used.
   * - Else if OUTPUT_FOLDER_ID env is set, it is used.
   * - Else it uploads to My Drive root of the service account.
   */
  const drive = getDriveClient();
  
  const parents =
    parentId ? [parentId] :
    (OUTPUT_FOLDER_ID ? [OUTPUT_FOLDER_ID] : undefined);
  
  const fileMetadata = { name, parents };
  
  const media = { mimeType: 'application/pdf', body: fs.createReadStream(localPath) };
  
  const res = await drive.files.create({
    requestBody: fileMetadata,
    media,
    fields: 'id, name, webViewLink, parents',
    supportsAllDrives: true
  });
  
  return res.data;
}

// ---- PDF fill (handles text / checkbox / radio / dropdown) ----
async function fillPdf(srcPath, outPath, fields = {}) {
  log('📝 Filling PDF with', Object.keys(fields).length, 'fields');
  
  const bytes = fs.readFileSync(srcPath);
  
  // IMPORTANT: Don't update appearances on load - we'll do it selectively
  // This preserves template fonts for Japanese text
  const pdfDoc = await PDFDocument.load(bytes, { updateFieldAppearances: false });
  
  let filled = 0;
  let form = null;
  const buttonFields = []; // Track button fields for appearance update
  
  try {
    form = pdfDoc.getForm();
  } catch (_) {
    log('⚠️  PDF has no form fields');
  }
  
  if (form) {
    for (const [key, rawVal] of Object.entries(fields)) {
      try {
        const f = form.getField(String(key));
        const typeName = (f && f.constructor && f.constructor.name) || '';
        const val = rawVal == null ? '' : String(rawVal);
        
        if (typeName.includes('Text')) {
          // Text fields: just set value, preserve template appearance/fonts
          f.setText(val);
          filled++;
        } else if (typeName.includes('Check')) {
          // Button fields: set value and track for appearance update
          const on = val.toLowerCase();
          if (on === 'true' || on === 'yes' || on === '1' || on === 'on') {
            f.check();
          } else {
            f.uncheck();
          }
          buttonFields.push(f);
          filled++;
        } else if (typeName.includes('Radio')) {
          try {
            f.select(val);
            buttonFields.push(f);
            filled++;
          } catch (_) {
            // Radio value not found - skip
          }
        } else if (typeName.includes('Dropdown')) {
          try {
            f.select(val);
            filled++;
          } catch (_) {
            // Dropdown value not found - skip
          }
        }
      } catch (_) {
        // Field not found — ignore missing field
      }
    }
    
    // Update appearances ONLY for button fields (checkboxes/radios)
    // This avoids font encoding issues with Japanese text in text fields
    if (buttonFields.length > 0) {
      try {
        // Update appearances for button fields only
        // pdf-lib doesn't have a direct API for this, so we'll update all fields
        // but catch errors for text fields
        for (const field of buttonFields) {
          try {
            field.updateAppearances();
          } catch (e) {
            // Ignore errors for individual fields
            log(`⚠️  Failed to update appearance for field: ${field.getName()}`);
          }
        }
      } catch (e) {
        log('⚠️  updateFieldAppearances failed:', e.message);
      }
    }
  }
  
  const outBytes = await pdfDoc.save();
  fs.writeFileSync(outPath, outBytes);
  
  log(`✅ Filled ${filled} fields, output size: ${outBytes.length} bytes`);
  
  return { outPath, filled, size: outBytes.length };
}

// ---- HTTP server ----
const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

app.get('/', (req, res) => {
  res.type('text/plain').send('PDF filler is up. Try GET /health');
});

app.get('/health', (req, res) => {
  res.json({
    ok: true,
    method: 'pdf-lib',
    tmpDir: TMP,
    hasOUTPUT_FOLDER_ID: !!OUTPUT_FOLDER_ID,
    credMode: process.env.GOOGLE_CREDENTIALS_JSON
      ? 'env-json'
      : (process.env.GOOGLE_APPLICATION_CREDENTIALS ? 'file-path' : 'adc/unknown')
  });
});

// GET /fields?fileId=XXXXXXXX — lists PDF form field names
app.get('/fields', async (req, res) => {
  try {
    const fileId = (req.query.fileId || '').trim();
    if (!fileId) {
      return res.status(400).json({ error: 'fileId is required' });
    }
    
    const localPath = path.join(TMP, `template_${fileId}.pdf`);
    await downloadDriveFile(fileId, localPath);
    
    const bytes = fs.readFileSync(localPath);
    const pdfDoc = await PDFDocument.load(bytes, { updateFieldAppearances: false });
    
    let names = [];
    try {
      const form = pdfDoc.getForm();
      const fields = form ? form.getFields() : [];
      names = fields.map(f => f.getName());
    } catch (_) {
      // No form fields
    }
    
    res.json({ count: names.length, names });
  } catch (e) {
    log('❌ List fields failed:', e && (e.stack || e));
    res.status(500).json({ error: 'List fields failed', detail: e && (e.message || String(e)) });
  }
});

// POST /fill
// body: { templateFileId: "<Drive file id>", fields: {...}, outputName?: "baseName", folderId?: "<Drive folder id>" }
app.post('/fill', async (req, res) => {
  try {
    const { templateFileId, fields, outputName, folderId } = req.body || {};
    
    if (!templateFileId) {
      return res.status(400).json({ error: 'templateFileId is required' });
    }
    
    if (!fields) {
      return res.status(400).json({ error: 'fields is required' });
    }
    
    // 1) Download template → 2) Fill → 3) Upload to Drive
    const tmpTemplate = path.join(TMP, `template_${templateFileId}.pdf`);
    await downloadDriveFile(templateFileId, tmpTemplate);
    
    const base = (outputName && String(outputName).trim()) || `filled_${Date.now()}`;
    const outName = base.toLowerCase().endsWith('.pdf') ? base : `${base}.pdf`;
    const outPath = path.join(TMP, outName);
    
    const result = await fillPdf(tmpTemplate, outPath, fields || {});
    
    log(`📤 Uploading to Drive: ${outName}`);
    const uploaded = await uploadToDrive(result.outPath, outName, folderId);
    
    log('✅ Uploaded to Drive:', uploaded.id);
    
    // Cleanup
    try {
      if (fs.existsSync(tmpTemplate)) fs.unlinkSync(tmpTemplate);
      if (fs.existsSync(outPath)) fs.unlinkSync(outPath);
    } catch (cleanupError) {
      log('⚠️  Cleanup failed:', cleanupError.message);
    }
    
    res.json({
      ok: true,
      filledCount: result.filled,
      driveFile: uploaded
    });
  } catch (err) {
    log('❌ ERROR /fill:', err && (err.stack || err));
    res.status(500).json({ error: 'Fill failed', detail: err && (err.message || String(err)) });
  }
});

app.listen(PORT, () => {
  log(`🚀 Server listening on ${PORT}`);
  log(`   OUTPUT_FOLDER_ID (fallback): ${OUTPUT_FOLDER_ID || '(none set)'}`);
  log(`   Creds: ${process.env.GOOGLE_CREDENTIALS_JSON ? 'GOOGLE_CREDENTIALS_JSON' :
              (process.env.GOOGLE_APPLICATION_CREDENTIALS ? 'GOOGLE_APPLICATION_CREDENTIALS' : 'ADC/unknown')}`);
});
