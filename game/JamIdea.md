GMTK Game Jam 2026 Theme: Countdown

Ideas:  
Bomb defusal  
timer/clock game  
Rocket launch  
Escape before time runs out  
Reverse number puzzle  
Platformer where your powers get less and less as the level progresses  
A stealth game where the guard’s patience runs lower and lower, and it gets worse each time you’re spotted   
2 things count down at once: less and less power from earlier, but the level also counts down; if you use the player’s powers, the level countdown slows and vice versa  
You start at the “end” of the level and have to jump your way to the beginning while terrain breaks behind you  
You’re building something, so that the countdown lands at 0 when you’re finished building it  
Countdown shrinks the world  
You’re on a diet, but you walk down one of the most full of fast food and other unhealthy things and must make it down the street without losing self-control.  
You die, and have to figure out where in a timeline of things that happened in your life caused that death and must reverse it.

Game:  
Title: Retrace

A platformer where you relive the final moments before your death, searching each one for the cause that could still be changed.

Core loop: The game counts down from 5 to 0 across five short platforming levels 5, 4, 3, 2, 1, each one a moment further back from the character's death, with 0 being the death itself. In each level, the player explores and interacts with objects to find the true cause, while red-herring objects give a clear "not it" cue rather than silence. Fixing the wrong thing doesn't end the game — it routes to a reused "still didn't work" outcome, keeping the game moving instead of hard-failing the player.

Theme tie-in (Countdown): The countdown isn't time — it's proximity to death, framed explicitly as 5→0 in the UI/level structure so it reads clearly as "countdown" at a glance. As the player investigates moments further back from death (higher countdown numbers), their character visibly fades — a fixed alpha value per level, not a real-time effect — mechanically and visually reinforcing that they're pulling further from their own present, and giving later levels a naturally harder, more obscured feel without extra tuning work.

Win condition: Find and flag the true cause at the correct moment; a clear confirmation cue (sound \+ visual, reusing existing particle/audio systems) signals success. No traditional fail-state — the player keeps investigating until they solve it, with escalating hints as a frustration safety net.

Scope for the jam: 3 levels to start (expand to 5 only if time allows), one real cause, one reusable "not yet" outcome, one win outcome, per-level fixed fade alpha on the player sprite.


Core playable loop (must-have, build first)

 Player movement + jump feel (gravity, coyote time, jump buffer) — physics.py in core, if not already ported
 Collision against get_solid_rects() — confirm it works against a real editor-made level, not just your test level
 State manager wired to actual states: Menu → Level Select/Intro → Playing → Death Scene → (loop or Win)
 One level (level 5, furthest back) fully playable start to finish, no clues yet — prove traversal works

Investigation mechanic (must-have)

 Interact system: proximity/keypress triggers on an object, not click (per earlier decision)
 Correct-clue object gives success feedback (sound + particle + UI confirmation)
 Red-herring objects give a "not it" cue (different sound/text, never silence)
 "Not yet" reusable outcome — what happens after a wrong flag (does the level restart? Do they keep exploring?)
 Win/advance trigger — flagging correct clue moves player to next level (4, then 3...) or shows countdown UI ticking

Countdown identity (must-have — this is your theme link, don't skip)

 Visible countdown UI (5→0) shown at level transitions
 Ghost fade — fixed alpha per level number on player sprite (cheapest version, static per level not animated)

Content (must-have, but scope-flex — cut levels before cutting polish)

 3 levels minimum (5, 3, 1 or similar spread) fully built in editor with tileset
 Level 0 (death scene) — composed scene, saturated palette, no player control, just observation/reveal
 Win-state scene — what does "successfully changed fate" look/feel like, even briefly

Juice (do after the above works, not before)

 Hit-flash / particle feedback on clue interactions (reuse particle system)
 Simple menu transition (fade or slide, not a hard cut)
 One ambient/ LMMS music track for memory levels, distinct sting or silence for death scene
 sfxr sounds: interact-success, interact-fail, level-transition, menu-select

Late-jam only (cut ruthlessly if short on time)

 Escalating hint system (diegetic text after N fails)
 Wind/tree/grass ambient dressing if levels have outdoor scenes — nice-to-have, not core
 Extra levels beyond 3
 Title screen art polish

Final hours (reserved, don't skip even if tight)

 Thumbnail — 30-60 min, tested at small size, per your process doc
 itch.io page: title, one-sentence pitch, controls listed clearly
 Playtest the first 30 seconds specifically — menu → first level → first interact
 Cohesion pass — palette/font/outline consistency check across all 3-4 levels