export function waitForFakeReady(child, { timeoutMs = 5000, stderr = () => '' } = {}) {
  return new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(
      () => fail(`fake startup deadline exceeded after ${timeoutMs} ms`),
      timeoutMs,
    );
    function cleanup() {
      clearTimeout(timer);
      child.off('error', onError);
      child.off('close', onClose);
      child.stdout.off('data', onData);
    }
    function fail(reason) {
      cleanup();
      reject(
        new Error(
          `${reason}; command=${JSON.stringify(child.spawnfile)}; exitCode=${child.exitCode}; signalCode=${child.signalCode}; stderr=${JSON.stringify(stderr())}`,
        ),
      );
    }
    function onError(error) {
      fail(`fake spawn failed: ${error.message}`);
    }
    // close, rather than exit, ensures the stderr stream has drained.
    function onClose() {
      fail('fake exited before readiness');
    }
    function onData(data) {
      output += data;
      if (!output.includes('\n')) return;
      const line = output.slice(0, output.indexOf('\n'));
      const port = Number(line);
      if (!/^\d+$/.test(line) || port < 1 || port > 65535) {
        fail('invalid fake readiness port');
        return;
      }
      cleanup();
      resolve(port);
    }
    child.once('error', onError);
    child.once('close', onClose);
    child.stdout.on('data', onData);
  });
}
