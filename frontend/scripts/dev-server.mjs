import { createServer } from 'vite'

const server = await createServer({
  configFile: './vite.config.ts',
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
})

await server.listen()
server.printUrls()

const shutdown = async () => {
  await server.close()
  process.exit(0)
}

process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)

// Keep the background process alive even when there is no interactive stdin.
setInterval(() => {}, 2_147_483_647)
