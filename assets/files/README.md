# Rick roll media

The lab terminal's two `.VID` files (`WATCH_IF_YOU_ARE_ROLLING` and
`WATCH_IF_YOU_ARE_NOT_ROLLING`) play whatever you put here.

- A video (`.mp4` / `.m4v` / `.mov` / `.webm` / `.mkv`): played with its own
  sound, streamed through `ffmpeg`, which has to be on the PATH (the `8-bit`
  conda env includes it; the Pi has it system-wide). Without it you get the GIF. The soundtrack is pulled out once and cached
  in `~/.cache/culture-shock/`. The repo ships `Rick Roll Link.mp4`.
- `rickroll.gif` (or `.png` / `.jpg` / `.webp`): the fallback picture when
  there's no ffmpeg. An animated GIF plays at its own frame rate (on pygame-ce,
  or through Pillow on plain pygame).
- `rickroll.ogg` (or `.mp3` / `.wav`): a song. It plays instead of the video's
  own sound, or alongside the picture. Playback ends when the song does.

Files named `rickroll.*` win; otherwise the first file with a matching extension
is used. A picture with no song runs for 20 seconds. With nothing playable, the
terminal says TAPE MISSING.
