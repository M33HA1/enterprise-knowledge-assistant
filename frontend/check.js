import { exec } from 'child_process';

exec('npm run lint', (err, stdout, stderr) => {
  console.log('stdout:', stdout);
  console.log('stderr:', stderr);
});
