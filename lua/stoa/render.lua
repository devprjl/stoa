local config = require 'stoa.config'

local M = {}

local width_of = vim.fn.strdisplaywidth

function M.wrap(text, width)
  local lines, line = {}, ''
  for word in text:gmatch '%S+' do
    if line == '' then
      line = word
    elseif width_of(line) + 1 + width_of(word) <= width then
      line = line .. ' ' .. word
    else
      lines[#lines + 1] = line
      line = word
    end
  end
  if line ~= '' then lines[#lines + 1] = line end
  return lines
end

function M.attribution(quote)
  local parts = {}
  if quote.author and quote.author ~= '' then parts[#parts + 1] = quote.author end
  if quote.work and quote.work ~= '' then parts[#parts + 1] = quote.work end
  return #parts > 0 and ('— ' .. table.concat(parts, ', ')) or ''
end

function M.art(quote, max_height)
  local art = quote.art or {}
  if max_height and art.large and #art.large > 0 and #art.large <= max_height then return art.large end
  if max_height and art.small and #art.small > 0 and #art.small <= max_height then return art.small end
  if not max_height then return art.large or art.small or {} end
  return {}
end

function M.credit(quote, width)
  local art = quote.art or {}
  if art.generated or not art.title then return nil end
  local parts = { art.title }
  if art.artist and art.artist ~= '' and art.artist ~= 'Unknown artist' then parts[#parts + 1] = art.artist end
  if art.museum then parts[#parts + 1] = art.museum end
  local text = table.concat(parts, ' · ')
  if width and width_of(text) > width then text = vim.fn.strcharpart(text, 0, math.max(1, width - 1)) .. '…' end
  return text
end

function M.text(quote, width)
  local lines = M.wrap('“' .. quote.text .. '”', math.max(20, math.min(config.options.view.wrap, width)))
  return lines, M.attribution(quote)
end

function M.build(quote, opts)
  local text, attribution = M.text(quote, opts.width - 4)
  local credit = opts.credit ~= false and M.credit(quote, opts.width - 4) or nil
  local reserved = #text + 3 + (opts.footer and 2 or 0) + (credit and 2 or 0)
  local art = M.art(quote, opts.height - reserved)
  if #art == 0 then credit = nil end

  local blocks = {}
  local function add(lines, group)
    for _, line in ipairs(lines) do
      blocks[#blocks + 1] = { line = line, group = group }
    end
  end
  add(art, 'StoaArt')
  if #art > 0 then add({ '' }, nil) end
  add(text, 'StoaQuote')
  add({ '' }, nil)
  add({ attribution }, 'StoaAuthor')
  if credit then
    add({ '' }, nil)
    add({ credit }, 'StoaHint')
  end
  if opts.footer then
    add({ '' }, nil)
    add({ opts.footer }, 'StoaHint')
  end

  local content_width = 0
  for _, block in ipairs(blocks) do
    content_width = math.max(content_width, width_of(block.line))
  end

  local top = opts.center and math.max(0, math.floor((opts.height - #blocks) / 2)) or 0
  local lines, marks = {}, {}
  for _ = 1, top do
    lines[#lines + 1] = ''
  end
  local span = opts.center and opts.width or content_width
  for _, block in ipairs(blocks) do
    local pad = math.max(0, math.floor((span - width_of(block.line)) / 2))
    lines[#lines + 1] = block.line == '' and '' or (' '):rep(pad) .. block.line
    if block.group then marks[#marks + 1] = { row = #lines - 1, group = block.group } end
  end
  return { lines = lines, marks = marks, width = content_width, height = #blocks }
end

function M.apply(buf, built)
  local ns = vim.api.nvim_create_namespace 'stoa'
  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, built.lines)
  vim.bo[buf].modifiable = false
  vim.bo[buf].modified = false
  vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
  for _, mark in ipairs(built.marks) do
    vim.api.nvim_buf_set_extmark(buf, ns, mark.row, 0, { end_row = mark.row + 1, hl_group = mark.group, hl_eol = false })
  end
end

function M.highlights()
  local links =
    { StoaArt = 'Function', StoaQuote = 'Normal', StoaAuthor = 'Comment', StoaHint = 'NonText', StoaBorder = 'FloatBorder', StoaTitle = 'FloatTitle' }
  for group, target in pairs(links) do
    vim.api.nvim_set_hl(0, group, { link = target, default = true })
  end
end

return M
