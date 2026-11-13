local config = require 'stoa.config'
local render = require 'stoa.render'

local M = {}

local chrome = { showtabline = 0, laststatus = 0 }
local saved = {}
local hiding = false

local function hide_chrome()
  hiding = true
  for name, hidden in pairs(chrome) do
    if vim.o[name] ~= hidden then
      saved[name] = vim.o[name]
      vim.o[name] = hidden
    end
  end
  hiding = false
end

local function restore_chrome()
  hiding = true
  for name in pairs(chrome) do
    if saved[name] ~= nil then
      vim.o[name] = saved[name]
      saved[name] = nil
    end
  end
  hiding = false
end

local function draw(buf, win)
  if not (vim.api.nvim_buf_is_valid(buf) and win ~= -1 and vim.api.nvim_win_is_valid(win)) then return end
  local built = render.build(require('stoa').current(), {
    width = vim.api.nvim_win_get_width(win),
    height = vim.api.nvim_win_get_height(win),
    center = true,
  })
  render.apply(buf, built)
  pcall(vim.api.nvim_win_set_cursor, win, { 1, 0 })
end

local function shortcuts(buf, win)
  local keys = vim.tbl_extend('force', {
    n = function()
      require('stoa').next()
      draw(buf, win)
    end,
  }, config.options.keys or {})
  for lhs, rhs in pairs(keys) do
    if rhs then vim.keymap.set('n', lhs, rhs, { buffer = buf, nowait = true, silent = true }) end
  end
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
  local window_options =
    { number = false, relativenumber = false, cursorline = false, list = false, wrap = false, signcolumn = 'no', foldcolumn = '0', statuscolumn = '' }
  for name, value in pairs(window_options) do
    vim.api.nvim_set_option_value(name, value, { scope = 'local', win = win })
  end

  hide_chrome()
  draw(buf, win)
  shortcuts(buf, win)

  local group = vim.api.nvim_create_augroup('stoa_splash_' .. buf, { clear = true })
  vim.api.nvim_create_autocmd({ 'VimResized', 'WinResized' }, {
    group = group,
    callback = function() draw(buf, vim.fn.bufwinid(buf)) end,
  })
  vim.api.nvim_create_autocmd('OptionSet', {
    group = group,
    pattern = { 'showtabline', 'laststatus' },
    callback = function()
      if hiding or vim.api.nvim_get_current_buf() ~= buf then return end
      vim.schedule(function()
        if vim.api.nvim_buf_is_valid(buf) and vim.api.nvim_get_current_buf() == buf then
          hide_chrome()
          draw(buf, vim.fn.bufwinid(buf))
        end
      end)
    end,
  })
  vim.api.nvim_create_autocmd('BufEnter', {
    group = group,
    buffer = buf,
    callback = function()
      hide_chrome()
      vim.schedule(function() draw(buf, vim.fn.bufwinid(buf)) end)
    end,
  })
  vim.api.nvim_create_autocmd({ 'BufLeave', 'BufWipeout' }, {
    group = group,
    buffer = buf,
    callback = function(args)
      restore_chrome()
      if args.event == 'BufWipeout' then pcall(vim.api.nvim_del_augroup_by_id, group) end
    end,
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
  if not config.options.dashboard then
    if vim.fn.exists ':Alpha' == 2 then return vim.cmd 'Alpha' end
    if vim.fn.exists ':Dashboard' == 2 then return vim.cmd 'Dashboard' end
    if type(rawget(_G, 'Snacks')) == 'table' and Snacks.dashboard then return Snacks.dashboard.open() end
  end
  if vim.bo.filetype == 'stoa' and vim.bo.buftype == 'nofile' then return end
  M.open()
end

return M
