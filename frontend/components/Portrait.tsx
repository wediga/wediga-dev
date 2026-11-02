import Image from "next/image";
import { PORTRAIT_SRC, cropStyle, type PortraitCrop } from "@/lib/portrait";

// The uploaded portrait with its crop, the same in the admin preview and on
// every page. className sets size and shape of the box the image is cut to.
// Unoptimized: the image changes with every upload, so the optimizer's cache
// would only serve a stale copy. Eager: wherever it appears, it is at the top.
export function Portrait({
  crop,
  alt,
  className,
  src = PORTRAIT_SRC,
}: {
  crop: PortraitCrop;
  alt: string;
  className: string;
  src?: string;
}) {
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <Image
        src={src}
        alt={alt}
        fill
        unoptimized
        loading="eager"
        draggable={false}
        className="object-cover"
        style={cropStyle(crop)}
      />
    </div>
  );
}
