Set Shell zsh
Set FontFamily "JetBrainsMono Nerd Font Mono"
Set FontSize 15
Set Width 1280
Set Height 860
Set Padding 0
Set TypingSpeed 0

Type "STOA_THEME=rose-pine STOA_AUTHOR='Marcus Aurelius' nvim -u scripts/screenshots/init.lua" Enter
Sleep 2s
Screenshot assets/marcus-aurelius.png
Type ":qa" Enter
Sleep 500ms

Type "STOA_THEME=tokyonight-night STOA_AUTHOR='Friedrich Nietzsche' nvim -u scripts/screenshots/init.lua" Enter
Sleep 2s
Screenshot assets/nietzsche.png
Type ":qa" Enter
Sleep 500ms

Type "STOA_THEME=catppuccin-mocha STOA_AUTHOR='Socrates' nvim -u scripts/screenshots/init.lua" Enter
Sleep 2s
Screenshot assets/socrates.png
Type ":qa" Enter
Sleep 500ms

Type "STOA_THEME=gruvbox STOA_AUTHOR='Seneca' nvim -u scripts/screenshots/init.lua" Enter
Sleep 2s
Screenshot assets/seneca.png
Type ":qa" Enter
Sleep 500ms

Type "STOA_THEME=kanagawa-wave STOA_AUTHOR='Aristotle' nvim -u scripts/screenshots/init.lua" Enter
Sleep 2s
Screenshot assets/aristotle.png
Type ":qa" Enter
Sleep 500ms

Type "STOA_THEME=everforest STOA_AUTHOR='Plato' STOA_FLOAT=1 nvim -u scripts/screenshots/init.lua lua/stoa/picker.lua" Enter
Sleep 1s
Type ":Stoa" Enter
Sleep 1s
Screenshot assets/float.png
Type "q"
Type ":qa" Enter
Sleep 500ms
