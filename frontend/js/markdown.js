// Everything is escaped first, so nothing in a reply can become HTML.

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function inline(text) {
  return text
    .split(/(`[^`]+`)/)
    .map((part) => part.startsWith("`") && part.endsWith("`") && part.length > 2
      ? `<code>${part.slice(1, -1)}</code>`
      : part
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/(^|[^*\w])\*([^*\n]+)\*/g, "$1<em>$2</em>")
        .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'))
    .join("");
}

const LIST_ITEM = /^(\s*)([-*•]|(\d+)[.)])\s+(.*)$/;
const FENCE = /^\s*```/;
const RULE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/;
const HEADING = /^#{1,6}\s+(.*)$/;
const TABLE_ROW = /^\s*\|.*\|\s*$/;
const TABLE_DIVIDER = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

function startsBlock(line, next = "") {
  return FENCE.test(line) || RULE.test(line) || HEADING.test(line) || LIST_ITEM.test(line)
    || line.startsWith("&gt;") || (TABLE_ROW.test(line) && TABLE_DIVIDER.test(next));
}

function renderList(lines) {
  let html = "";
  const open = [];
  for (const line of lines) {
    if (!LIST_ITEM.test(line)) {
      html += `<br>${inline(line.trim())}`;
      continue;
    }
    const [, space, , number, text] = line.match(LIST_ITEM);
    const indent = space.length;
    const tag = number ? "ol" : "ul";
    while (open.length && indent < open.at(-1).indent) html += `</li></${open.pop().tag}>`;
    const top = open.at(-1);
    if (!top || indent > top.indent) {
      html += `<${tag}${number && number !== "1" ? ` start="${number}"` : ""}>`;
      open.push({ indent, tag });
    } else {
      html += "</li>";
      if (top.tag !== tag) {
        html += `</${top.tag}><${tag}${number && number !== "1" ? ` start="${number}"` : ""}>`;
        top.tag = tag;
      }
    }
    html += `<li>${inline(text)}`;
  }
  while (open.length) html += `</li></${open.pop().tag}>`;
  return html;
}

function renderTable(lines) {
  const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => inline(cell.trim()));
  const [head, , ...rows] = lines;
  const th = cells(head).map((c) => `<th>${c}</th>`).join("");
  const body = rows.map((row) => `<tr>${cells(row).map((c) => `<td>${c}</td>`).join("")}</tr>`).join("");
  return `<div class="table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function renderMarkdown(source) {
  const lines = escapeHtml(source).split("\n");
  const html = [];
  let i = 0;
  const take = (test) => {
    const taken = [];
    while (i < lines.length && test(lines[i])) taken.push(lines[i++]);
    return taken;
  };

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    if (FENCE.test(line)) {
      i++;
      const code = take((l) => !FENCE.test(l));
      i++;
      html.push(`<pre><code>${code.join("\n")}</code></pre>`);
    } else if (TABLE_ROW.test(line) && TABLE_DIVIDER.test(lines[i + 1] || "")) {
      html.push(renderTable(take((l) => TABLE_ROW.test(l))));
    } else if (RULE.test(line)) {
      html.push("<hr>");
      i++;
    } else if (HEADING.test(line)) {
      html.push(`<h3>${inline(line.match(HEADING)[1])}</h3>`);
      i++;
    } else if (LIST_ITEM.test(line)) {
      html.push(renderList(take((l) => LIST_ITEM.test(l) || /^\s+\S/.test(l))));
    } else if (line.startsWith("&gt;")) {
      const quote = take((l) => l.startsWith("&gt;")).map((l) => l.replace(/^&gt;\s?/, ""));
      html.push(`<blockquote>${inline(quote.join("<br>"))}</blockquote>`);
    } else {
      const paragraph = [lines[i++]];
      while (i < lines.length && lines[i].trim() && !startsBlock(lines[i], lines[i + 1])) paragraph.push(lines[i++]);
      html.push(`<p>${inline(paragraph.join("<br>"))}</p>`);
    }
  }
  return html.join("");
}
