// Test launcher only: no outbound Node networking; relocate legacy debug writes.
import net from 'node:net';
import dns from 'node:dns';
import fs from 'node:fs';
import path from 'node:path';
import { syncBuiltinESMExports } from 'node:module';

function trap() {
  fs.appendFileSync(process.env.REHEARSAL_EGRESS_TRAP, 'blocked outbound attempt\n');
}
net.Socket.prototype.connect = function () {
  trap();
  throw new Error('rehearsal blocks Node network connections');
};
dns.lookup = function () {
  trap();
  throw new Error('rehearsal blocks Node DNS lookups');
};
for (const method of ['mkdir', 'appendFile']) {
  const original = fs.promises[method].bind(fs.promises);
  fs.promises[method] = function (target, ...args) {
    const text = String(target);
    if (text.endsWith('/logs') || text.endsWith('/logs/nodejs_debug.log')) {
      target = text.endsWith('/logs')
        ? process.env.REHEARSAL_LOG_DIR
        : path.join(process.env.REHEARSAL_LOG_DIR, 'nodejs_debug.log');
    }
    return original(target, ...args);
  };
}
syncBuiltinESMExports();
