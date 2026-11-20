# Remotion image scenes

Goal: use uploaded images in reusable animated scenes, edit parameters in local FE, preview immediately, export through the existing job queue.

Architecture: one React composition shared by Remotion Player and Node Remotion renderer. Project config selects growkaz or remotion (existing projects default to growkaz). Each shot retains timing in story/shots.json and gets a visual object. Python API still stores projects and queues jobs. No Whisper integration and no generative image animation.

Tasks:
1. Test engine selection, scene readiness, asset containment and job dispatch.
2. Create composition, predictable timeline/frame conversion and export runner.
3. Add image-scene editor with layer selection, camera preset, title/subtitle and live preview.
4. Connect existing contact-sheet, preview, full-render and audio mix jobs.
5. Test backend and timeline; typecheck/build; inspect stills before full render; test UI and actual MP4 export.

Quality: eased camera motion, image cover, alpha overlays, aspect-aware typography, safe margins, gentle fades, preserved source colors. One foreground image layer, no automatic skeletal rigging or object separation. Missing imagery can use an explicit gradient placeholder. Existing GrowKaz modules remain unchanged.
