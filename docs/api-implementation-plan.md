# Local animation API implementation plan

Goal: connect a frontend exported from Google AI Studio to the existing local animation engine.
Architecture: FastAPI on loopback, filesystem projects, one render worker, polled job status. Existing Node renderer stays unchanged. No remote hosting or automatic scene generation.

1. Test project creation, duplicate rejection, upload containment, shot timing validation, render preconditions and job results.
2. Implement project/config/story/assets endpoints and protected artifact downloads.
3. Implement serial background renderer jobs, bounded logs, failure detection and stale job recovery.
4. Add startup command, frontend contract, TypeScript client and AI Studio prompt.
5. Run unit/integration tests and an actual preview render through HTTP.

Constraints: no overwrite of existing project folders; no arbitrary shell commands; validate slugs and paths; never expose parent workspace. Upload images/audio/text only. Bind loopback. CORS defaults to localhost:5173 and localhost:3000. One API process; no uvicorn reload during render.

Design decision: create empty projects or explicitly clone the built-in demo. Uploaded pictures are stored for scene authoring; uploading does not itself attach them to a shot. Shot editing changes timing/metadata, not JavaScript scene code. Full render produces silent video; mixing is a separate job requiring narration. Whisper model is not downloaded by setup.
