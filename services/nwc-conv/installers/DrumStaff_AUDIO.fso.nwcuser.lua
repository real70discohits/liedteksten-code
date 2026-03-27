-- Version 0.1

--[[--------------------------------------------------------------------------

This plugin is intended to make things a little easier for writing drums and percussion music.

The 'General MIDI Percussion Key Map' does not correspond with actual standard used in the written music for drums, so DrumStaff tries to solve this problem.
DrumStaff consists in two different objects: This one adds playback support to DrumStaff.

To enable DrumStaff sounds just follow the next instructions:

- Set the staff MIDI Channel to 10, because drums sounds are usually played at this MIDI channel.
- Transpose your percussion cleff staff up by 4 octaves (Staff Properties/Instrument/Transposition/+48). That's only for security reasons, because we don't want to overlap sounds.
- Insert an instance of this plugin at the start of your staff and, on properties, click the checkbox to enable playback.
- After this you will need to insert a new (playback enabled) instance at the end of each meassure. This is the most important (and annoying) step, because if the 'end instance' is not found for too many meassures the plugin will crash and NWC2 will disable it.

Remember that:
- Drums sounds plays at MIDI Channel 10 so, please, don't forget to set the Staff MIDI Channel to 10.
- Although you will see only one meassure, Multi-Meassure Rest meassures count for more (as many as MMR says). Disable playback before the MMR, and re-enable it when needed.
- There's lots of play styles and drum tecniques but General MIDI hasn't a sound for each one, so BuzzRoll and Double Stroke Rolls are not supported, and other plugins have no effect over the sound. You can writte them, but they can't be played. Sorry.
- Although other plugins have no effect over the sound, dynamics are supported.
- You can enable/disable sound of any DrumStaff_AUDIO instance with '+' hotkey.

This plugin is intended to be used with Visual enhancements of 'DrumStaff'.

--]]--------------------------------------------------------------------------


local userObjTypeName = ...
local NextNote = nwc.ntnidx.new()
local NextDyn = nwc.ntnidx.new()
local QIdx = nwc.ntnidx.new()

local Vel1 = 64
local Vel2 = 64
local Vel = 64



local object_spec = {
{ id='InOut', label='Sound Enable', type='bool', default=1 },
}



local function do_spin(t,d)

	if t.InOut then t.InOut = 1+d
	elseif not t.InOut then t.InOut = 0+d
	end

end



local function do_play(t)

  if not t.InOut then return
  else

    if not NextNote:find('next', 'user', userObjTypeName) then
	return
    else

	while NextNote:find('prior', 'note') do
		local xNotePos = NextNote:sppOffset()
		if xNotePos >= 0 then

			local yNotePos1 = NextNote:notePitchPos(1)
			local yNotePos2 = NextNote:notePitchPos(2)
			local yNotePos3 = NextNote:notePitchPos(3)
			local yNotePos4 = NextNote:notePitchPos(4)
			local NoteDur = NextNote:durationBase()
			local Length = nwcplay.calcDurLength(NoteDur)

			--DYNAMICS
			    local Dyn1 = NextDyn:find('prior','dynamic')
			    local DynPos1 = NextDyn:sppOffset()
			    local DynProp1 = NextDyn:objProp('Style')

			    if DynProp1 == 'ppp' then Vel1 = 10
			    	elseif DynProp1 == 'pp' then Vel1 = 30
				    elseif DynProp1 == 'p' then Vel1 = 45
				    elseif DynProp1 == 'mp' then Vel1 = 60
				    elseif DynProp1 == 'mf' then Vel1 = 75
				    elseif DynProp1 == 'f' then Vel1 = 92
				    elseif DynProp1 == 'ff' then Vel1 = 108
				    elseif DynProp1 == 'fff' then Vel1 = 127
			    end
			    NextDyn:reset()

			    local Dyn2 = NextDyn:find('next','dynamic')
			    local DynPos2 = NextDyn:sppOffset()
			    local DynProp2 = NextDyn:objProp('Style')

			    if DynProp2 == 'ppp' then Vel2 = 10
				    elseif DynProp2 == 'pp' then Vel2 = 30
				    elseif DynProp2 == 'p' then Vel2 = 45
				    elseif DynProp2 == 'mp' then Vel2 = 60
				    elseif DynProp2 == 'mf' then Vel2 = 75
				    elseif DynProp2 == 'f' then Vel2 = 92
				    elseif DynProp2 == 'ff' then Vel2 = 108
				    elseif DynProp2 == 'fff' then Vel2 = 127
			    end
			    NextDyn:reset()

			    if DynPos2<=xNotePos then Vel = Vel2
			    else Vel = Vel1
			    end

			--BASS DRUM
			if yNotePos1 == '-3o' or yNotePos2 == '-3o' or yNotePos3 == '-3o' or yNotePos4 == '-3o' then
				nwcplay.note(xNotePos,Length,36,Vel)
				nwcplay.midi(xNotePos,2,93,0)
			end
			--SNARE DRUM
			if yNotePos1 == '1o' or yNotePos2 == '1o' or yNotePos3 == '1o' or yNotePos4 == '1o' then
				nwcplay.note(xNotePos,Length,38,Vel)
				nwcplay.midi(xNotePos,2,100,0)
			end
			--SNARE Rim Shot
			if yNotePos1 == '1z' or yNotePos2 == '1z' or yNotePos3 == '1z' or yNotePos4 == '1z' then
				nwcplay.note(xNotePos,Length,40,Vel)
				nwcplay.midi(xNotePos,2,100,0)
			end
			--SNARE Cross Stick
			if yNotePos1 == '1f' or yNotePos2 == '1f' or yNotePos3 == '1f' or yNotePos4 == '1f' then
				nwcplay.note(xNotePos,Length,37,Vel)
				nwcplay.midi(xNotePos,2,100,0)
			end
			--SNARE Ghost Note
			if yNotePos1 == '1Y' or yNotePos2 == '1Y' or yNotePos3 == '1Y' or yNotePos4 == '1Y' then
				nwcplay.note(xNotePos,Length,38,Vel/1.75)
				nwcplay.midi(xNotePos,2,100,0)
			end
			--TOM add (1)
			if yNotePos1 == '3o' or yNotePos2 == '3o' or yNotePos3 == '3o' or yNotePos4 == '3o' then
				nwcplay.note(xNotePos,Length,48,Vel)
				nwcplay.midi(xNotePos,2,103,0)
			end
			--TOM 1
			if yNotePos1 == '2o' or yNotePos2 == '2o' or yNotePos3 == '2o' or yNotePos4 == '2o' then
				nwcplay.note(xNotePos,Length,47,Vel)
				nwcplay.midi(xNotePos,2,101,0)
			end
			--TOM 2
			if yNotePos1 == '0o' or yNotePos2 == '0o' or yNotePos3 == '0o' or yNotePos4 == '0o' then
				nwcplay.note(xNotePos,Length,45,Vel)
				nwcplay.midi(xNotePos,2,98,0)
			end
			--TOM 3
			if yNotePos1 == '-1o' or yNotePos2 == '-1o' or yNotePos3 == '-1o' or yNotePos4 == '-1o' then
				nwcplay.note(xNotePos,Length,43,Vel)
				nwcplay.midi(xNotePos,2,96,0)
			end
			--TOM add (2)
			if yNotePos1 == '-2o' or yNotePos2 == '-2o' or yNotePos3 == '-2o' or yNotePos4 == '-2o' then
				nwcplay.note(xNotePos,Length,41,Vel)
				nwcplay.midi(xNotePos,2,95,0)
			end
			--HI-HAT Open
			if yNotePos1 == '5y' or yNotePos2 == '5y' or yNotePos3 == '5y' or yNotePos4 == '5y' then
				nwcplay.note(xNotePos,Length,46,Vel)
				nwcplay.midi(xNotePos,2,107,0)
			end
			--HI-HAT Close
			if yNotePos1 == '5x' or yNotePos2 == '5x' or yNotePos3 == '5x' or yNotePos4 == '5x' then
				nwcplay.note(xNotePos,Length,42,Vel)
				nwcplay.midi(xNotePos,2,107,0)
			end
			--HI-HAT Foot
			if yNotePos1 == '-5x' or yNotePos2 == '-5x' or yNotePos3 == '-5x' or yNotePos4 == '-5x' then
				nwcplay.note(xNotePos,Length,44,Vel)
				nwcplay.midi(xNotePos,2,89,0)
				end
			--HI-HAT Foot Splash
			if yNotePos1 == '-5z' or yNotePos2 == '-5z' or yNotePos3 == '-5z' or yNotePos4 == '-5z' then
				nwcplay.note(xNotePos,Length,55,Vel)
				nwcplay.midi(xNotePos,2,89,0)
				end
			--RIDE
			if yNotePos1 == '4x' or yNotePos2 == '4x' or yNotePos3 == '4x' or yNotePos4 == '4x' then
				nwcplay.note(xNotePos,Length,51,Vel)
				nwcplay.midi(xNotePos,2,105,0)
			end
			--RIDE Bell
			if yNotePos1 == '4h' or yNotePos2 == '4h' or yNotePos3 == '4h' or yNotePos4 == '4h' then
				nwcplay.note(xNotePos,Length,53,Vel)
				nwcplay.midi(xNotePos,2,105,0)
			end
			--CRASH
			if yNotePos1 == '6z' or yNotePos2 == '6z' or yNotePos3 == '6z' or yNotePos4 == '6z' then
				nwcplay.note(xNotePos,Length,49,Vel)
				nwcplay.midi(xNotePos,2,108,0)
			end
			--SPLASH
			if yNotePos1 == '7X' or yNotePos2 == '7X' or yNotePos3 == '7X' or yNotePos4 == '7X' then
				nwcplay.note(xNotePos,Length,55,Vel)
				nwcplay.midi(xNotePos,2,110,0)
			end
			--COWBELL
			if yNotePos1 == '7a' or yNotePos2 == '7a' or yNotePos3 == '7a' or yNotePos4 == '7a' then
				nwcplay.note(xNotePos,Length,56,Vel)
				nwcplay.midi(xNotePos,2,110,0)
			end

		end
	end
    end
  end

end



local function do_create(t)

	t.Class = 'StaffSig'

  if not QIdx:find('prior', 'user', userObjTypeName) then
	nwcui.msgbox('REMEMBER:\n\n-Set the staff MIDI Channel to 10.\n- Transpose your staff up 4 Octaves (Staff Properties/Instrument/Transposition/+48).\n- One instance at the beginning of the staff.\n- One instance at the end of each meassure.\n\nEnjoy drumming...', 'DrumStaff Remembering...')
  end

end


local function do_draw(t)

if not NextNote:find('prior', 'user', userObjTypeName) then
  if not t.InOut then
	local w = nwc.toolbox.drawStaffSigLabel('DS:Off')
	if not nwcdraw.isDrawing() then return w end
  else
	local w = nwc.toolbox.drawStaffSigLabel('DS:Audio')
	if not nwcdraw.isDrawing() then return w end
  end
else
  if not t.InOut then
	local w = nwc.toolbox.drawStaffSigLabel('DS:Off')
	if not nwcdraw.isDrawing() then return w end
  else
	local w = nwc.toolbox.drawStaffSigLabel('DS:On')
	if not nwcdraw.isDrawing() then return w end
  end
end

end


return {
	spec = object_spec,
	create = do_create,
	spin = do_spin,
	width = do_draw,
	draw = do_draw,
	play = do_play,
}