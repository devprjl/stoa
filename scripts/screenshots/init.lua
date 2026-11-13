local root = vim.fs.dirname(vim.fs.dirname(vim.fs.dirname(vim.fs.normalize(vim.fn.fnamemodify(debug.getinfo(1, 'S').source:sub(2), ':p')))))
local themes = vim.env.STOA_THEMES or (vim.fn.stdpath 'data' .. '/lazy')
local theme = vim.env.STOA_THEME or 'rose-pine'
local plugin = { ['rose-pine'] = 'rose-pine', ['tokyonight-night'] = 'tokyonight.nvim', ['catppuccin-mocha'] = 'catppuccin', ['kanagawa-wave'] = 'kanagawa.nvim', gruvbox = 'gruvbox.nvim', everforest = 'everforest-nvim' }

vim.opt.runtimepath:prepend(root)
vim.opt.runtimepath:append(themes .. '/' .. (plugin[theme] or theme))
vim.o.termguicolors = true
vim.o.showmode = false
vim.o.ruler = false
vim.o.fillchars = 'eob: '
vim.o.shadafile = 'NONE'
pcall(vim.cmd.colorscheme, theme)

local stoa = require 'stoa'
stoa.setup { dashboard = vim.env.STOA_FLOAT == nil, sync = { enabled = false }, paths = { state = vim.fn.tempname() } }

local wanted = vim.env.STOA_AUTHOR
if wanted then
  local picker = require 'stoa.picker'
  for _, quote in ipairs(require('stoa.store').quotes()) do
    if quote.author == wanted then
      picker.pick = function() return picker.resolve(quote) end
    end
  end
end
vim.cmd 'runtime plugin/stoa.lua'
