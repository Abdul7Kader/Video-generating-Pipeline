import net from 'node:net';

export function loopbackListenArguments(args) {
  const [first, ...rest] = args;
  const localHost = (host) => {
    if (host == null || ['0.0.0.0', '::', 'localhost', '127.0.0.1', '::1'].includes(host)) return '127.0.0.1';
    throw new Error('Renderer-Server dürfen nur auf Loopback lauschen.');
  };
  if (first && typeof first === 'object' && 'port' in first) return [{...first, host:localHost(first.host)}, ...rest];
  if (typeof first === 'number') {
    if (typeof rest[0] === 'string') return [first, localHost(rest[0]), ...rest.slice(1)];
    return [first, '127.0.0.1', ...rest];
  }
  throw new Error('Nicht unterstützter Renderer-Serverstart; nur lokale TCP-Ports sind erlaubt.');
}

export function enforceLoopbackListeners() {
  // Process-local guard: Remotion currently creates wildcard HTTP listeners internally.
  // No firewall, operating-system setting or dependency file is changed.
  const original = net.Server.prototype.listen;
  net.Server.prototype.listen = function (...args) {
    return original.apply(this, loopbackListenArguments(args));
  };
  return () => {net.Server.prototype.listen = original;};
}
