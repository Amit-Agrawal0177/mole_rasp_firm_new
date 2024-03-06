const { spawn } = require('child_process');
const pythonOptions = { env: { PYTHONUNBUFFERED: '1' } };
const { exec } = require('child_process');
const NodeMediaServer = require('node-media-server');
/*
function checkInternet() {
  return new Promise((resolve, reject) => {
    exec('ping -c 1 google.com', (error, stdout, stderr) => {
      if (error) {
        reject(stderr || error);  // Capture error output
        return;
      }

      // Check if the ping was successful
      const isOnline = stdout.includes('1 packets transmitted, 1 received');
      resolve(isOnline);
    });
  });
}

function checkInternetDNS() {
  return new Promise((resolve) => {
    require('dns').resolve('www.google.com', function (err) {
      resolve(!err); // Resolve to true if DNS resolution succeeds, indicating internet connectivity
    });
  });
}

async function waitForInternet() {
  while (true) {
    try {
      const online = await checkInternetDNS(); // Use DNS resolution for internet connectivity check

      if (online) 
      {
        console.log('Internet is present.');

        break; 
      }

      console.log('Internet is not present. Waiting for it to become available...');
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait for 5 seconds before checking again
    } catch (error) {
      console.error('Error checking internet connectivity:', error);
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait for 5 seconds before checking again in case of an error
    }
  }
}

waitForInternet();
* 
* 
  //streamingLocal();
  //savingVideo();
  //localDirAccess();
  //sendGpsData();
  * 
*/
//sudo systemctl daemon-reload
//sudo systemctl start myscript.service
//sudo systemctl enable myscript.service
//sudo systemctl status myscript.service


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
