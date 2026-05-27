/** EXIF tag ids for capture timestamps (decimal). */
const EXIF_DATETIME_ORIGINAL = 36867;
const EXIF_DATETIME_DIGITIZED = 36868;
const EXIF_DATETIME = 306;
const EXIF_DATE_TAGS = [EXIF_DATETIME_ORIGINAL, EXIF_DATETIME_DIGITIZED, EXIF_DATETIME];

const EXIF_DATE_PATTERNS = [
  /^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})$/,
  /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/,
];

function parseExifDateTime(value: string): string | null {
  const cleaned = value.trim();
  for (const pattern of EXIF_DATE_PATTERNS) {
    const match = pattern.exec(cleaned);
    if (!match) continue;
    const [, year, month, day, hour, minute, second] = match;
    return `${year}-${month}-${day}T${hour}:${minute}:${second}Z`;
  }
  return null;
}

function readAscii(view: DataView, offset: number, length: number): string {
  let value = "";
  for (let index = 0; index < length - 1; index += 1) {
    const code = view.getUint8(offset + index);
    if (code === 0) break;
    value += String.fromCharCode(code);
  }
  return value;
}

function readUint16(view: DataView, offset: number, littleEndian: boolean): number {
  return view.getUint16(offset, littleEndian);
}

function readUint32(view: DataView, offset: number, littleEndian: boolean): number {
  return view.getUint32(offset, littleEndian);
}

function readIfdDate(
  view: DataView,
  tiffOffset: number,
  ifdOffset: number,
  littleEndian: boolean
): string | null {
  if (ifdOffset + 2 > view.byteLength) return null;

  const entryCount = readUint16(view, ifdOffset, littleEndian);
  let entryOffset = ifdOffset + 2;

  for (let index = 0; index < entryCount; index += 1) {
    if (entryOffset + 12 > view.byteLength) return null;

    const tag = readUint16(view, entryOffset, littleEndian);
    if (EXIF_DATE_TAGS.includes(tag)) {
      const type = readUint16(view, entryOffset + 2, littleEndian);
      const count = readUint32(view, entryOffset + 4, littleEndian);
      if (type !== 2 || count < 2) return null;

      let valueOffset = entryOffset + 8;
      if (count > 4) {
        valueOffset = tiffOffset + readUint32(view, entryOffset + 8, littleEndian);
      }

      if (valueOffset + count > view.byteLength) return null;
      const raw = readAscii(view, valueOffset, count);
      const parsed = parseExifDateTime(raw);
      if (parsed) return parsed;
    }

    entryOffset += 12;
  }

  return null;
}

/** Read capture date from JPEG EXIF bytes before client-side re-encoding. */
export function extractCaptureDateFromJpegBytes(buffer: Uint8Array): string | null {
  if (buffer.length < 4 || buffer[0] !== 0xff || buffer[1] !== 0xd8) {
    return null;
  }

  let offset = 2;
  while (offset + 4 < buffer.length) {
    if (buffer[offset] !== 0xff) {
      offset += 1;
      continue;
    }

    const marker = buffer[offset + 1];
    if (marker === 0xd9 || marker === 0xda) break;

    const segmentLength = (buffer[offset + 2] << 8) + buffer[offset + 3];
    if (segmentLength < 2 || offset + 2 + segmentLength > buffer.length) break;

    if (marker === 0xe1) {
      const header = String.fromCharCode(...buffer.slice(offset + 4, offset + 10));
      if (header === "Exif\u0000\u0000") {
        const tiffOffset = offset + 10;
        if (tiffOffset + 8 > buffer.length) return null;

        const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
        const byteOrder = String.fromCharCode(view.getUint8(tiffOffset), view.getUint8(tiffOffset + 1));
        const littleEndian = byteOrder === "II";
        if (byteOrder !== "II" && byteOrder !== "MM") return null;

        const ifd0Offset = tiffOffset + readUint32(view, tiffOffset + 4, littleEndian);
        const exifIfdPointerOffset = findTagOffset(view, ifd0Offset, 34665, littleEndian);
        if (exifIfdPointerOffset != null) {
          const exifIfdOffset = tiffOffset + readUint32(view, exifIfdPointerOffset, littleEndian);
          const fromExif = readIfdDate(view, tiffOffset, exifIfdOffset, littleEndian);
          if (fromExif) return fromExif;
        }

        const fromIfd0 = readIfdDate(view, tiffOffset, ifd0Offset, littleEndian);
        if (fromIfd0) return fromIfd0;
      }
    }

    offset += 2 + segmentLength;
  }

  return null;
}

function findTagOffset(
  view: DataView,
  ifdOffset: number,
  tag: number,
  littleEndian: boolean
): number | null {
  if (ifdOffset + 2 > view.byteLength) return null;

  const entryCount = readUint16(view, ifdOffset, littleEndian);
  let entryOffset = ifdOffset + 2;

  for (let index = 0; index < entryCount; index += 1) {
    if (entryOffset + 12 > view.byteLength) return null;
    const entryTag = readUint16(view, entryOffset, littleEndian);
    if (entryTag === tag) {
      return entryOffset + 8;
    }
    entryOffset += 12;
  }

  return null;
}

export async function extractPhotoCaptureDate(file: File): Promise<string | null> {
  if (file.type !== "image/jpeg" && !file.name.toLowerCase().endsWith(".jpg") && !file.name.toLowerCase().endsWith(".jpeg")) {
    return null;
  }

  const header = await readFileHeader(file, 256 * 1024);
  return extractCaptureDateFromJpegBytes(header);
}

async function readFileHeader(file: File, maxBytes: number): Promise<Uint8Array> {
  const slice = file.slice(0, maxBytes);
  const buffer = await blobToArrayBuffer(slice);
  return new Uint8Array(buffer);
}

function blobToArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === "function") {
    return blob.arrayBuffer();
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error ?? new Error("Could not read file."));
    reader.readAsArrayBuffer(blob);
  });
}
