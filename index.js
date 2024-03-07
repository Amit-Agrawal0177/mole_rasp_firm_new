const { spawn } = require('child_process');
const pythonOptions = { env: { PYTHONUNBUFFERED: '1' } };
const { exec } = require('child_process');
const NodeMediaServer = require('node-media-server');

const config = {
  rtmp: {
    port: 1935, // RTMP port
    chunk_size: 100000, // Size of each chunk in bytes
  },
  http: {
    port: 8000, // HTTP port
    allow_origin: '*', // Cross-origin resource sharing
  },
};

const nms = new NodeMediaServer(config);
nms.run();

function startProcess() {  
  streamingGlobal();
  sensePirMovment();
  senseAdxlMovment();
  fileToS3();
  saveArray();
  playAudio();
  //networkCheck();
}

console.log("Server Start");

setTimeout(() => {
  console.log("Timeout completed after 2000 milliseconds");
  startProcess();
}, 5000);

console.log("End");

function streamingLocal() {
  const localProcess = spawn('python', ['py_scripts/streaming_local.py']);

  localProcess.stdout.on('data', (data) => {
    console.log(`localOut: ${data}`);
  });

  localProcess.stderr.on('data', (data) => {
    console.error(`localErr: ${data}`);
  });

  localProcess.on('close', (code) => {
    console.log(`local child process exited with code ${code}`);
    streamingLocal();
  });
}

function streamingGlobal() {
  const streamingProcess = spawn('python', ['py_scripts/streaming_script.py']);

  streamingProcess.stdout.on('data', (data) => {
    console.log(`streamingOut: ${data}`);
  });

  streamingProcess.stderr.on('data', (data) => {
    console.error(`streamingErr: ${data}`);
  });

  streamingProcess.on('close', (code) => {
    console.log(`streaming child process exited with code ${code}`);
    streamingGlobal();
  });
}

function sensePirMovment() {
  const movementProcess = spawn('python', ['py_scripts/pir_mqtt.py']);

  movementProcess.stdout.on('data', (data) => {
    console.log(`pir movementOut: ${data}`);
  });

  movementProcess.stderr.on('data', (data) => {
    console.error(`pir movementErr: ${data}`);
  });

  movementProcess.on('close', (code) => {
    console.log(`pir movement child process exited with code ${code}`);
    sensePirMovment();
  });
}

function senseAdxlMovment() {
  const movementProcess = spawn('python', ['py_scripts/gps_adxl_pir.py']);

  movementProcess.stdout.on('data', (data) => {
    console.log(`Adxl movementOut: ${data}`);
  });

  movementProcess.stderr.on('data', (data) => {
    console.error(`Adxl movementErr: ${data}`);
  });

  movementProcess.on('close', (code) => {
    console.log(`Adxl movement child process exited with code ${code}`);
    senseAdxlMovment();
  });
}

function savingVideo() {
  const recordingProcess = spawn('python', ['py_scripts/videoRecording.py']);

  recordingProcess.stdout.on('data', (data) => {
    console.log(`recordingOut: ${data}`);
  });

  recordingProcess.stderr.on('data', (data) => {
    console.error(`recordingErr: ${data}`);
  });

  recordingProcess.on('close', (code) => {
    console.log(`recording child process exited with code ${code}`);
    savingVideo();
  });
}

function fileToS3() {
  const s3Process = spawn('python', ['py_scripts/videoToServer.py']);

  s3Process.stdout.on('data', (data) => {
    console.log(`s3Out: ${data}`);
  });

  s3Process.stderr.on('data', (data) => {
   console.error(`s3Err: ${data}`);
  });

  s3Process.on('close', (code) => {
    console.log(`s3 child process exited with code ${code}`);
    fileToS3();
  });
}

function localDirAccess() {
  const ftpProcess = spawn('python', ['py_scripts/ftp.py']);

  ftpProcess.stdout.on('data', (data) => {
    console.log(`ftpProcessOut: ${data}`);
  });

  ftpProcess.stderr.on('data', (data) => {
    console.error(`ftpProcessErr: ${data}`);
  });

  ftpProcess.on('close', (code) => {
    console.log(`ftpProcess child process exited with code ${code}`);
    localDirAccess();
  });
}

function networkCheck() {

  const nrProcess = spawn('python', ['py_scripts/networkRestart.py']);

  nrProcess.stdout.on('data', (data) => {
    console.log(`networkRestart Out: ${data}`);
  });

  nrProcess.stderr.on('data', (data) => {
    console.error(`networkRestart Err: ${data}`);
  });

  nrProcess.on('close', (code) => {
    console.log(`networkRestart child process exited with code ${code}`);
    networkCheck();
  });
}

function saveArray() {

  const nrProcess = spawn('python', ['py_scripts/Data2Server.py']);

  nrProcess.stdout.on('data', (data) => {
    console.log(`saveArray Out: ${data}`);
  });

  nrProcess.stderr.on('data', (data) => {
    console.error(`saveArray Err: ${data}`);
  });

  nrProcess.on('close', (code) => {
    console.log(`saveArray child process exited with code ${code}`);
    saveArray();
  });
}

function playAudio() {

  const nrProcess = spawn('python', ['py_scripts/playAudio.py']);

  nrProcess.stdout.on('data', (data) => {
    console.log(`playAudio Out: ${data}`);
  });

  nrProcess.stderr.on('data', (data) => {
    console.error(`playAudio Err: ${data}`);
  });

  nrProcess.on('close', (code) => {
    console.log(`playAudio child process exited with code ${code}`);
    playAudio();
  });
}
