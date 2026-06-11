import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

// Renders markdown server-side into React elements. react-markdown escapes
// through React and disables raw HTML by default, and rehype-sanitize strips
// anything outside its safe schema, so no unsanitised HTML ever reaches the
// browser and there is no dangerouslySetInnerHTML.
export function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-3 leading-relaxed [&_a]:underline [&_h1]:text-xl [&_h1]:font-bold [&_h2]:text-lg [&_h2]:font-semibold">
      <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{children}</ReactMarkdown>
    </div>
  );
}
