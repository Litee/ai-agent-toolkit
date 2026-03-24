# Embeds Reference

Embeds display content inline using `![[...]]` syntax (an exclamation mark before a wikilink).

## Note Embeds

Embed the full content of another note:
```
![[Note Name]]
```

Embed from a specific heading to the next heading of equal or higher level:
```
![[Note Name#Heading]]
```

Embed a specific block (requires a block ID on the source block):
```
![[Note Name#^block-id]]
```

Embed a heading or block from the current note:
```
![[#Heading]]
![[#^block-id]]
```

## Image Embeds

Local images (in vault or attachment folder):
```
![[image.png]]              — full size
![[image.png|300]]          — width 300px, height proportional
![[image.png|300x200]]      — exact width × height in pixels
```

External images (standard Markdown syntax):
```
![Alt text](https://example.com/image.png)
![Alt text|300](https://example.com/image.png)
```

Supported formats: PNG, JPG/JPEG, GIF, BMP, SVG, WEBP

## PDF Embeds

```
![[document.pdf]]               — full PDF viewer
![[document.pdf#page=3]]        — open at page 3
![[document.pdf#height=400]]    — viewer with height 400px
```

## Audio Embeds

```
![[recording.mp3]]
![[audio.ogg]]
![[podcast.m4a]]
```

Supported formats: MP3, WebM, WAV, M4A, OGG, 3GP, FLAC

Renders an inline audio player.

## Video Embeds

```
![[screencast.mp4]]
![[demo.webm]]
```

Supported formats: MP4, WebM, OGV, MOV, MKV, OGM, OGX

Renders an inline video player.

## List Embeds

Embed a list by referencing its block ID:

Source note (`My Lists`):
```
- Item one
- Item two
- Item three
^my-list
```

Embedding note:
```
![[My Lists#^my-list]]
```

## Query Block Embeds

Embed dynamic search results using a `query` fenced code block:

````
```query
tag:#project status:done
```
````

The results update live as the vault changes.

## Sizing Summary

| Content | Width only | Width × Height |
|---------|-----------|----------------|
| Images | `\|300` | `\|300x200` |
| PDFs | — | `#height=400` |
| Notes/blocks | — | — (auto) |
