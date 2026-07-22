# Jam Checklist

## Before the jam (do this now, not at hour 0)
- [ ] Confirm the template still runs cold: `pip install -r requirements.txt && python main.py`
- [ ] Update `pygame` / deps if there's a newer stable version
- [ ] Skim `core/` for TODOs left over from the last jam's retro

## Hour 0 - setup
- [ ] "Use this template" -> new repo for the jam game
- [ ] Rename the repo, update the README title
- [ ] Confirm the theme, decide the one-sentence pitch
- [ ] Do NOT edit `core/` yet - if you think you need to, write it down and come back to it

## During the jam
- [ ] All jam-specific code goes in `game/` - `core/` is read-only unless you hit an actual bug
- [ ] Drop sfx into `assets/sfx/`, music into `assets/music/`, UI art into `assets/palette_ui/`
- [ ] If `core/` is missing something, hack around it in `game/` first; fix `core/` properly in the post-jam retro
- [ ] Commit often - a broken build at hour 80 is recoverable, a lost 6 hours of work isn't

## Before submitting
- [ ] Test a fresh clone/build, not just your dev machine
- [ ] Strip debug keybinds / cheat codes, or gate them behind a flag
- [ ] Volume defaults are sane; window resize/fullscreen doesn't crash
- [ ] README has: how to run, controls, credits

## Post-jam retro (do this within a few days, while it's fresh)
- [ ] What did I have to hack around in `core/`? Fix it properly now.
- [ ] What was missing entirely? Add a stub or a real implementation.
- [ ] What in `game/` turned out to be generic enough for `core/`? Promote it.
- [ ] Tag the toolkit repo (`v1.x`) once changes land.
- [ ] Reset this jam's `game/` contents back to empty on the template.
