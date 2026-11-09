import { createConnection } from "node:net";
import { join } from "node:path";
export function request(directory: string, command: object): Promise<any> {
  return new Promise((resolve, reject) => {
    const socket = createConnection(join(directory, "run.sock"));
    let input = "";
    socket.setTimeout(10000, () => socket.destroy(new Error("Coordinator did not respond")));
    socket.on("error", reject);
    socket.on("connect", () => socket.write(JSON.stringify(command) + "\n"));
    socket.on("data", chunk => { input += chunk.toString(); if (Buffer.byteLength(input) > 4 * 1024 * 1024) socket.destroy(new Error("Coordinator response too large")); });
    socket.on("end", () => {
      try { const response = JSON.parse(input); if (!response.ok) reject(new Error(response.error)); else resolve(response.result); }
      catch (error) { reject(error); }
    });
  });
}
