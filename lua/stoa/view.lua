local config = require 'stoa.config'
local render = require 'stoa.render'

local M = {}

local state = { win = nil, buf = nil, quote = nil }

local function close()
  if state.win and vim.api.nvim_win_is_valid(state.win) then vim.api.nvim_win_close(state.win, true) end
  state.win, state.buf = nil, nil
end

local function layout(quote)
  local columns, rows = vim.o.columns, vim.o.lines - vim.o.cmdheight - 1
  local built = render.build(quote, { width = math.max(24, columns - 8), height = math.max(6, rows - 4), footer = 'n next   y copy   q close' })
  local width = math.min(columns - 4, built.width + 6)
  local height = math.min(rows - 2, built.height + 2)
  local centered = { lines = { '' }, marks = {} }
  for i, line in ipairs(built.lines) do
    local trimmed = line:gsub('^%s+', '')
    local pad = math.max(0, math.floor((width - vim.fn.strdisplaywidth(trimmed)) / 2))
    centered.lines[i + 1] = trimmed == '' and '' or (' '):rep(pad) .. trimmed
  end
  for _, mark in ipairs(built.marks) do
    centered.marks[#centered.marks + 1] = { row = mark.row + 1, group = mark.group }
  end
  centered.lines[#centered.lines + 1] = ''
  return centered,
    {
      relative = 'editor',
      style = 'minimal',
      border = config.options.view.border,
      title = config.options.view.title,
      title_pos = 'center',
      width = width,
      height = height,
      row = math.max(0, math.floor((rows - height) / 2) - 1),
      col = math.max(0, math.floor((columns - width) / 2) - 1),
    }
end

local function draw(quote)
  state.quote = quote
  local built, win_config = layout(quote)
  render.apply(state.buf, built)
  if state.win and vim.api.nvim_win_is_valid(state.win) then
    vim.api.nvim_win_set_config(state.win, win_config)
  else
    state.win = vim.api.nvim_open_win(state.buf, true, win_config)
    vim.wo[state.win].winhighlight = 'FloatBorder:StoaBorder,FloatTitle:StoaTitle'
    vim.wo[state.win].wrap = false
    vim.wo[state.win].cursorline = false
  end
  vim.api.nvim_win_set_cursor(state.win, { 1, 0 })
end

function M.open(quote)
  close()
  render.highlights()
  state.buf = vim.api.nvim_create_buf(false, true)
  vim.bo[state.buf].bufhidden = 'wipe'
  vim.bo[state.buf].filetype = 'stoa'
  draw(quote)

  local function map(lhs, rhs) vim.keymap.set('n', lhs, rhs, { buffer = state.buf, nowait = true, silent = true }) end
  map('q', close)
  map('<Esc>', close)
  map('n', function() draw(require('stoa').next()) end)
  map('y', function() require('stoa').copy() end)
  vim.api.nvim_create_autocmd('VimResized', {
    buffer = state.buf,
    callback = function()
      if state.buf and state.quote then draw(state.quote) end
    end,
  })
  vim.api.nvim_create_autocmd('WinLeave', { buffer = state.buf, once = true, callback = close })
end

return M
