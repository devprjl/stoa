local M = {}

local function defaults()
  return {
    categories = nil,
    dashboard = false,
    keys = {},
    quote_command = true,
    sync = {
      enabled = true,
      interval = 86400,
      timeout = 8,
      urls = {
        'https://cdn.jsdelivr.net/gh/itzzsauravp/stoa.nvim@main/data',
        'https://raw.githubusercontent.com/itzzsauravp/stoa.nvim/main/data',
      },
    },
    view = { border = 'rounded', title = ' stoa ', wrap = 64 },
    paths = {
      state = vim.fn.stdpath 'state' .. '/stoa',
      pack = vim.fn.stdpath 'data' .. '/stoa',
    },
  }
end

M.options = defaults()

function M.setup(opts) M.options = vim.tbl_deep_extend('force', defaults(), opts or {}) end

return M
