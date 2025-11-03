// PDF Filler using pikepdf - Set values only, preserve template fonts and appearances
// This approach sets /V and /AS without updating appearances, letting PDF viewer handle display

const fs = require('fs');
const os = require('os');
const path = require('path');
const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const { promisify } = require('util');
const { google } = require('googleapis');

const PORT = process.env.PORT || 8080;
const TMP = path.join(os.tmpdir(), 'pdf-filler-pikepdf');
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

// Execute command with arguments array (safer than shell string)
function execAsyncArray(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(command, args, {
      ...options,
      stdio: ['ignore', 'pipe', 'pipe']
    });
    
    let stdout = '';
    let stderr = '';
    
    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    proc.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`Command failed with code ${code}: ${stderr}`));
      }
    });
    
    proc.on('error', (error) => {
      reject(error);
    });
  });
}

// ---- Google Drive client (supports Shared Drives) ----
function getDriveClient() {
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

// ---- PDF fill using pikepdf - Set values only, preserve template appearances ----
async function fillPdf(srcPath, outPath, fields = {}) {
  log('📝 Filling PDF with', Object.keys(fields).length, 'fields');
  
  const pythonScript = path.join(__dirname, 'pdf_filler_pikepdf.py');
  const fieldsJson = JSON.stringify(fields);
  
  const cmdArgs = [
    pythonScript,
    srcPath,
    outPath,
    '--fields', fieldsJson
  ];
  
  log('🔧 Running: python3 pdf_filler_pikepdf.py [template] [output] --fields [JSON]');
  
  try {
    const { stdout, stderr } = await execAsyncArray('python3', cmdArgs, {
      maxBuffer: 10 * 1024 * 1024 // 10MB buffer
    });
    
    if (stdout) {
      console.log(`📊 pikepdf output: ${stdout.trim()}`);
      try {
        const result = JSON.parse(stdout.split('\n').filter(l => l.trim().startsWith('{')).pop() || '{}');
        if (result.filled_count !== undefined) {
          log(`✅ Filled ${result.filled_count} fields`);
        }
      } catch (e) {
        // Ignore JSON parse errors
      }
    }
    
    if (stderr && !stderr.includes('⚠️')) {
      console.warn(`⚠️  pikepdf stderr: ${stderr}`);
    }
    
    if (!fs.existsSync(outPath)) {
      throw new Error('Output file was not created');
    }
    
    const outputSize = fs.statSync(outPath).size;
    log(`✅ PDF filled successfully`);
    log(`   Output size: ${outputSize} bytes`);
    
    return { outPath, filled: Object.keys(fields).length, size: outputSize };
    
  } catch (error) {
    log(`❌ pikepdf error: ${error.message}`);
    throw new Error(`pikepdf failed: ${error.message}`);
  }
}

// Check if pikepdf (Python) is available
async function checkPikepdf() {
  try {
    const { stdout } = await execAsyncArray('python3', ['-c', 'import pikepdf; print(pikepdf.__version__)']);
    log(`✅ pikepdf found: ${stdout.trim()}`);
    return true;
  } catch (error) {
    log(`❌ pikepdf not found: ${error.message}`);
    return false;
  }
}

// ---- HTTP server ----
const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

app.get('/', (req, res) => {
  res.type('text/plain').send('PDF filler is up. Try GET /health');
});

app.get('/health', async (req, res) => {
  const pikepdfAvailable = await checkPikepdf();
  res.json({
    ok: true,
    method: 'pikepdf',
    pikepdfAvailable,
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
    
    // Use pikepdf to list fields
    const pythonScript = path.join(__dirname, 'pdf_filler_pikepdf.py');
    const { stdout } = await execAsyncArray('python3', [
      pythonScript,
      localPath,
      '/dev/null', // dummy output
      '--fields', '{}',
      '--list-fields'
    ]);
    
    let names = [];
    try {
      const result = JSON.parse(stdout.split('\n').filter(l => l.trim().startsWith('{')).pop() || '{}');
      names = result.field_names || [];
    } catch (_) {
      // Ignore parse errors
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
    
    // Check if pikepdf is available
    const pikepdfAvailable = await checkPikepdf();
    if (!pikepdfAvailable) {
      return res.status(500).json({ 
        error: 'pikepdf not available', 
        detail: 'pikepdf (Python) is required but not installed on this system' 
      });
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
