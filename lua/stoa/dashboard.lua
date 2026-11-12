local render = require 'stoa.render'

local M = {}

local hint = 'n next quote   e new file   q quit'

local function draw(buf, win)
  if not (vim.api.nvim_buf_is_valid(buf) and vim.api.nvim_win_is_valid(win)) then return end
  local built = render.build(require('stoa').current(), {
    width = vim.api.nvim_win_get_width(win),
    height = vim.api.nvim_win_get_height(win),
    center = true,
    footer = hint,
  })
  render.apply(buf, built)
end

function M.open()
  render.highlights()
  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].bufhidden = 'wipe'
  vim.bo[buf].buftype = 'nofile'
  vim.bo[buf].swapfile = false
  vim.api.nvim_set_current_buf(buf)
  vim.bo[buf].filetype = 'stoa'

  local win = vim.api.nvim_get_current_win()
  for name, value in pairs {
    number = false,
    relativenumber = false,
    cursorline = false,
    list = false,
    wrap = false,
    signcolumn = 'no',
    foldcolumn = '0',
    statuscolumn = '',
  } do
    vim.api.nvim_set_option_value(name, value, { scope = 'local', win = win })
  end

  draw(buf, win)

  local function map(lhs, rhs) vim.keymap.set('n', lhs, rhs, { buffer = buf, nowait = true, silent = true }) end
  map('n', function()
    require('stoa').next()
    draw(buf, win)
  end)
  map('e', '<cmd>enew<CR>')
  map('q', '<cmd>qa<CR>')

  vim.api.nvim_create_autocmd({ 'VimResized', 'WinResized' }, {
    buffer = buf,
    callback = function() draw(buf, vim.fn.bufwinid(buf)) end,
  })
end

local function blank_start()
  if vim.fn.argc(-1) > 0 or vim.bo.filetype ~= '' or vim.bo.modified then return false end
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  return #lines <= 1 and (lines[1] or '') == ''
end

function M.enable()
  local group = vim.api.nvim_create_augroup('stoa_dashboard', { clear = true })
  local function start()
    if blank_start() then M.open() end
  end
  if vim.v.vim_did_enter == 1 then
    start()
  else
    vim.api.nvim_create_autocmd('VimEnter', { group = group, once = true, nested = true, callback = start })
  end
end

function M.home()
  local config = require 'stoa.config'
  if not config.options.dashboard then
    if vim.fn.exists ':Alpha' == 2 then return vim.cmd 'Alpha' end
    if vim.fn.exists ':Dashboard' == 2 then return vim.cmd 'Dashboard' end
    if type(rawget(_G, 'Snacks')) == 'table' and Snacks.dashboard then return Snacks.dashboard.open() end
  end
  M.open()
end

return M
