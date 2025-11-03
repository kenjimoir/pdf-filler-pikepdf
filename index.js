// PDF Filler using pikepdf - Modern Python library for excellent Japanese text support
// This service uses pikepdf (Python) instead of PDFtk for better Unicode and font handling

const fs = require('fs');
const os = require('os');
const path = require('path');
const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const { promisify } = require('util');
const { google } = require('googleapis');

const execAsync = promisify(exec);

// Render.com uses port 10000 by default, Railway uses dynamic port
const PORT = process.env.PORT || 8080;
const TMP = path.join(os.tmpdir(), 'pdf-filler-pikepdf');
const OUTPUT_FOLDER_ID = process.env.OUTPUT_FOLDER_ID;

// Ensure temp directory exists
if (!fs.existsSync(TMP)) {
  fs.mkdirSync(TMP, { recursive: true });
}

// Initialize Google Drive client
function getDriveClient() {
  // Option 1: JSON string in environment variable
  if (process.env.GOOGLE_CREDENTIALS_JSON) {
    try {
      const creds = JSON.parse(process.env.GOOGLE_CREDENTIALS_JSON);
      const auth = new google.auth.GoogleAuth({
        credentials: creds,
        scopes: ['https://www.googleapis.com/auth/drive'],
      });
      return google.drive({ version: 'v3', auth });
    } catch (parseError) {
      throw new Error(`Invalid GOOGLE_CREDENTIALS_JSON: ${parseError.message}`);
    }
  }
  
  // Option 2: File path in environment variable (Render file-based secrets)
  if (process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    const auth = new google.auth.GoogleAuth({
      keyFile: process.env.GOOGLE_APPLICATION_CREDENTIALS,
      scopes: ['https://www.googleapis.com/auth/drive'],
    });
    return google.drive({ version: 'v3', auth });
  }
  
  throw new Error('Either GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS must be set');
}

// Fill PDF using pikepdf (Python) - Modern approach with better Unicode support
async function fillPdfWithPikepdf(templatePath, outputPath, fields, opts) {
  const options = Object.assign({ regenerate_appearances: true, flatten: false }, opts);
  if (String(options.flattenMethod || '').toLowerCase() === 'none') {
    options.flatten = false;
  }
  
  console.log(`📝 Filling PDF with pikepdf...`);
  console.log(`   Template: ${templatePath}`);
  console.log(`   Output: ${outputPath}`);
  console.log(`   Fields: ${Object.keys(fields).length}`);
  
  try {
    // Prepare fields JSON (escape for shell)
    const fieldsJson = JSON.stringify(fields).replace(/"/g, '\\"');
    
    // Build Python command
    const pythonScript = path.join(__dirname, 'pdf_filler_pikepdf.py');
    const cmdArgs = [
      'python3',
      pythonScript,
      templatePath,
      outputPath,
      '--fields', fieldsJson
    ];
    
    if (options.regenerate_appearances) {
      cmdArgs.push('--regenerate-appearances');
    } else {
      cmdArgs.push('--no-regenerate-appearances');
    }
    
    if (options.flatten) {
      cmdArgs.push('--flatten');
    }
    
    const cmd = cmdArgs.map(arg => {
      // Quote arguments that contain spaces or special characters
      if (arg.includes(' ') || arg.includes('"') || arg.includes("'")) {
        return `"${arg.replace(/"/g, '\\"')}"`;
      }
      return arg;
    }).join(' ');
    
    console.log(`🔧 Running: python3 pdf_filler_pikepdf.py [template] [output] --fields [JSON]`);
    
    const { stdout, stderr } = await execAsync(cmd, {
      maxBuffer: 10 * 1024 * 1024 // 10MB buffer for large outputs
    });
    
    if (stdout) {
      console.log(`📊 pikepdf output: ${stdout.trim()}`);
      try {
        const result = JSON.parse(stdout.split('\n').filter(l => l.trim().startsWith('{')).pop() || '{}');
        if (result.filled_count !== undefined) {
          console.log(`✅ Filled ${result.filled_count} fields`);
        }
      } catch (e) {
        // Ignore JSON parse errors for stdout
      }
    }
    
    if (stderr && !stderr.includes('⚠️')) {
      console.warn(`⚠️  pikepdf stderr: ${stderr}`);
    }
    
    // Check if output file exists
    if (!fs.existsSync(outputPath)) {
      throw new Error('Output file was not created');
    }
    
    const outputSize = fs.statSync(outputPath).size;
    console.log(`✅ PDF filled successfully with pikepdf`);
    console.log(`   Output size: ${outputSize} bytes`);
    
    return { success: true, size: outputSize, method: 'pikepdf' };
    
  } catch (error) {
    console.error(`❌ pikepdf error: ${error.message}`);
    throw new Error(`pikepdf failed: ${error.message}`);
  }
}

// Upload to Google Drive
async function uploadToDrive(drive, filePath, fileName, folderId) {
  // If folderId is provided, verify it exists and is accessible
  const finalFolderId = folderId || OUTPUT_FOLDER_ID;
  if (finalFolderId) {
    try {
      await drive.files.get({
        fileId: finalFolderId,
        fields: 'id, name, mimeType',
        supportsAllDrives: true,
      });
      console.log(`✅ Verified folder exists: ${finalFolderId}`);
    } catch (error) {
      if (error.code === 404) {
        throw new Error(`Folder not found: ${finalFolderId}. Please check:\n1. Folder ID is correct\n2. Folder is shared with service account\n3. If in Shared Drive, service account has access`);
      } else if (error.code === 403) {
        throw new Error(`Access denied to folder: ${finalFolderId}. Please share the folder with your service account email.`);
      }
      throw error;
    }
  }
  
  const parents = finalFolderId ? [finalFolderId] : [];
  
  const fileMetadata = {
    name: fileName,
    parents: parents.length > 0 ? parents : undefined,
  };
  
  const media = {
    mimeType: 'application/pdf',
    body: fs.createReadStream(filePath),
  };
  
  const file = await drive.files.create({
    requestBody: fileMetadata,
    media: media,
    fields: 'id, name, webViewLink, webContentLink',
    supportsAllDrives: true,
  });
  
  return file.data;
}

// Check if pikepdf (Python) is available
async function checkPikepdf() {
  try {
    const { stdout } = await execAsync('python3 -c "import pikepdf; print(pikepdf.__version__)"');
    console.log(`✅ pikepdf found: ${stdout.trim()}`);
    return true;
  } catch (error) {
    console.error(`❌ pikepdf not found: ${error.message}`);
    return false;
  }
}

// HTTP Server
const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

app.get('/', (_req, res) => {
  res.json({ service: 'PDF Filler (pikepdf)', status: 'running' });
});

app.get('/health', async (_req, res) => {
  const pikepdfAvailable = await checkPikepdf();
  res.json({
    ok: true,
    pikepdfAvailable,
    method: 'pikepdf',
    outputFolder: OUTPUT_FOLDER_ID || 'not set',
    tempDir: TMP,
  });
});

app.post('/fill', async (req, res) => {
  const { templateFileId, fields, outputName, folderId, mode, flattenMethod } = req.body;
  
  if (!templateFileId || !fields) {
    return res.status(400).json({ error: 'Missing templateFileId or fields' });
  }
  
  // Check if pikepdf is available
  const pikepdfAvailable = await checkPikepdf();
  if (!pikepdfAvailable) {
    return res.status(500).json({ 
      error: 'pikepdf not available', 
      detail: 'pikepdf (Python) is required but not installed on this system' 
    });
  }
  
  const drive = getDriveClient();
  const templatePath = path.join(TMP, `template_${templateFileId}.pdf`);
  const outputPath = path.join(TMP, `output_${Date.now()}.pdf`);
  
  try {
    // 0. Inspect template metadata
    const meta = await drive.files.get({
      fileId: templateFileId,
      fields: 'id, name, mimeType, size, owners(emailAddress)',
      supportsAllDrives: true,
    });
    console.log(`📄 Template meta: name=${meta.data.name} mime=${meta.data.mimeType} size=${meta.data.size}`);

    // 1. Download template (export if it's a Google Doc)
    console.log(`📥 Downloading template: ${templateFileId}`);
    if (meta.data.mimeType && meta.data.mimeType.startsWith('application/vnd.google-apps')) {
      // Not a binary PDF on Drive → export as PDF
      const exportRes = await drive.files.export(
        { fileId: templateFileId, mimeType: 'application/pdf' },
        { responseType: 'stream' }
      );
      const writeStream = fs.createWriteStream(templatePath);
      exportRes.data.pipe(writeStream);
      await new Promise((resolve, reject) => {
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
      });
    } else {
      const templateFile = await drive.files.get(
        { fileId: templateFileId, alt: 'media', supportsAllDrives: true },
        { responseType: 'stream' }
      );
      const writeStream = fs.createWriteStream(templatePath);
      templateFile.data.pipe(writeStream);
      await new Promise((resolve, reject) => {
        writeStream.on('finish', resolve);
        writeStream.on('error', reject);
      });
    }
    console.log('✅ Template downloaded');
    
    const modeStr = String(mode || 'final').toLowerCase();
    if (modeStr === 'copy') {
      // Just pass-through the template to output (sanity check)
      console.log('🧪 COPY mode: uploading template as-is');
      fs.copyFileSync(templatePath, outputPath);
    } else {
      // 2. Fill PDF with pikepdf
      console.log(`📝 Filling PDF with ${Object.keys(fields).length} fields...`);
      const flatten = modeStr !== 'preview';
      const fm = String(flattenMethod || 'none').toLowerCase();
      
      await fillPdfWithPikepdf(templatePath, outputPath, fields, { 
        flatten: flatten,
        flattenMethod: fm,
        regenerate_appearances: true 
      });
    }
    
    // 3. Upload to Drive
    const finalName = outputName || `filled_${Date.now()}.pdf`;
    console.log(`📤 Uploading to Drive: ${finalName}`);
    const uploadedFile = await uploadToDrive(
      drive,
      outputPath,
      finalName,
      folderId || OUTPUT_FOLDER_ID
    );
    
    // Cleanup
    try {
      if (fs.existsSync(templatePath)) {
        fs.unlinkSync(templatePath);
      }
      if (fs.existsSync(outputPath)) {
        fs.unlinkSync(outputPath);
      }
    } catch (cleanupError) {
      console.warn(`⚠️ Cleanup failed: ${cleanupError.message}`);
    }
    
    res.json({
      ok: true,
      driveFile: uploadedFile,
      method: 'pikepdf',
    });
    
  } catch (error) {
    console.error('❌ Error:', error);
    res.status(500).json({
      error: 'Fill failed',
      detail: error.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 PDF Filler (pikepdf) running on port ${PORT}`);
  console.log(`   Temp directory: ${TMP}`);
  console.log(`   Output folder: ${OUTPUT_FOLDER_ID || 'not set'}`);
});

