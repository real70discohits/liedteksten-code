--Version 0.1

--[[--------------------------------------------------------------------------

This plugin is intended to make things a little easier for writing drums and percussion music.

The 'General MIDI Percussion Key Map' does not correspond with actual standard used in the written music for drums, so DrumStaff tries to solve this problem.
DrumStaff consists in two different objects: This one improves notation by the adition of some Custom Noteheads and other usual marks.

To enable the Custom Noteheads just insert this object at the start of the staff.
Object's Class have to be set to "StaffSig" to make Custom Noteheads work properly. After this you only have to insert notes on their correct staff positions.
The 'Drum Key' used for this plugin is detailed as follows: (in a staff with 'Percussion' or 'Bass' Clef)


-Bass Drum (A1)
-Snare Drum (E2)
-Tom-Toms (G2-F2-D2-C2-B1)
-Hi-Hat Cymbal (B2)
-Hi-Hat Foot (F1)
-Ride Cymbal (A2)
-Crash Cymbal (C3)
-Others (D4)


The different tecniques or the elements missing are determined by the Noteheads and other marks (X for cymbals, or snare Rim Shot, 'o' and '+' for open and closed Hi-Hat, etc.).
For using the Custom Noteheads you will have to insert the drum/cymbal element at the correct staff position, then select the apropiate NWC Notehead. The plugin automatically will turn the usual Notehead into the Custom one as follows:

- 'Blank Space' in the Snare Drum position (E2) turns Rim Shot.
- 'Shape 5 - so' in the Snare Drum position (E2) turns Cross Stick.
- 'Non-Pitched' in the Hi-Hat Cymbal position (B2) turns Open HH.
- 'X' in the Hi-Hat Cymbal position (B2) turns Closed HH.
- 'Blank Space' in the Hi-Hat Foot position (F1) turns Splash HH.
- 'Blank Space' in the Crash position (C3) turns Crash Cymbals.

Other usual NWC marks must be compatible, like staccatos in Crash Cymbals (for Choked Crash) and text markings or other user objects for some snare tecniques like Buzz Roll or Double Stroke Roll.
Also the rest of usual NWC Noteheads are allowed for specific elements (Ride Bell, Splash Cymbal, Cowbell, etc.)

In case that the open/closed Hi-Hat markings were unnecessary they can be disabled from the plugin properties. In that case use 'X' notehead (closed Hi-Hat) all the time.

In adition, DrumStaff offers some other markings to use not only in Drums notation: (object's class must be 'Standard' for those ones)

- METRIC MODULATION: this options lets to easily add symbols like 'Tempo Figure=Tempo Figure' to the staff. Both first and second tempo marks are fully selectable and combinable and the full mark can be scaled.
- MALLETS/STICKS: this options inserts icons and (or) labels for some types of mallets and sticks. Both icons and labels are independent and can be scaled, otherwise, the text style in labels will be Bold Italic.

This plugin is intended to be used with 'DrumStaff_AUDIO', which correctly plays drum sounds written with this object.

--]]--------------------------------------------------------------------------


local userObjTypeName = ...
local QIdx = nwc.ntnidx.new()

local NoteHeads = nwc.drawpos.new()
local ZeroIDX = nwc.drawpos.new()

local TempoList1 = { 'Eighth', 'Eighth Dotted', 'Quarter', 'Quarter Dotted', 'Half', 'Half Dotted' }
local TempoList2 = { 'Eighth', 'Eighth Dotted', 'Quarter', 'Quarter Dotted', 'Half', 'Half Dotted' }
local StickList = { 'None', 'Sticks', 'Brushes', 'Hard Mallets', 'Soft Mallets', 'Mixed Mallets' } 

local symbols = { Half = 'F', Quarter = 'G', Eighth = 'H' }
local dot = 'z'


---------------------------------------------------------------------------------------------------


local object_spec = {
{ id='HiHat', label='NOTEHEADS: Use mark for closed Hi-Hat', type='bool', default=false, },
{ id='MetricMod', label='Insert METRIC MODULATION mark:', type='bool', default=false },
{ id='T1', label='1st Tempo Figure', type='enum', default=TempoList1[1], list=TempoList1 },
{ id='T2', label='2nd Tempo Figure', type='enum', default=TempoList2[1], list=TempoList2 },
{ id='Scale1', label='Scale (%)', type='int', min=5, max=400, step=5, default=100 },
{ id='Sticks', label='Insert MALLETS/STICKS mark:', type='bool', default=false },
{ id='Icons', label='Icon', type='enum', default=StickList[1], list=StickList },
{ id='Scale2', label='Icon Scale (%)', type='int', min=5, max=400, step=5, default=75 },
{ id='label', label='Label', type='text', default='' },
{ id='Scale3', label='Label Scale (%)', type='int', min=5, max=400, step=5, default=50 },
}


---------------------------------------------------------------------------------------------------


local function do_create(t)

  if not QIdx:find('prior', 'user', userObjTypeName) then
	if nwcui.askbox('This is the first time inserting this object at this staff.\nCustom Noteheads will only show properly if the first object´s class is set to StaffSig.\n\nDo you want to use this object for enable Custom Noteheads?', 'DrumStaff Custom Noteheads', 1) == 1 then
		t.Class = 'StaffSig'
	else
		t.Class = 'Standard'
	end
  end

end


---------------------------------------------------------------------------------------------------


local function width(t)

  if t.Class == 'StaffSig' then
	local w = nwc.toolbox.drawStaffSigLabel(userObjSigName)
	if not nwcdraw.isDrawing() then return w end
  end

end


---------------------------------------------------------------------------------------------------


local function do_draw(t)

--CUSTOM NOTEHEADS--

  if t.Class == 'Standard' and not t.MetricMod and not t.Sticks then
	local w = nwc.toolbox.drawStaffSigLabel('XXXX')
	if not nwcdraw.isDrawing() then return w end
  end

  if t.Class == 'StaffSig' then
	local w = nwc.toolbox.drawStaffSigLabel('DS:Visual')
	if not nwcdraw.isDrawing() then return w end
  end

  if t.Class == 'StaffSig' then
	while NoteHeads:find('next','note') do
		local xNotePos = NoteHeads:sppOffset()
		ZeroIDX:find('first')
		local x0, y0 = ZeroIDX:xyAnchor()

		local yNotePos1 = NoteHeads:notePitchPos(1)
		local yNotePos2 = NoteHeads:notePitchPos(2)
		local yNotePos3 = NoteHeads:notePitchPos(3)
		local yNotePos4 = NoteHeads:notePitchPos(4)

		--SNARE Rim Shot
		if yNotePos1 == '1z' or yNotePos2 == '1z' or yNotePos3 == '1z' or yNotePos4 == '1z' then
			nwcdraw.setFontClass('StaffSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*100*.01)
			local x1z, y1z = NoteHeads:xyTimeslot()
			nwcdraw.moveTo(x1z+0.55, y0+1)
			nwcdraw.alignText('baseline','center')
			nwcdraw.text('g')
		end
		--SNARE Cross Stick
		if yNotePos1 == '1f' or yNotePos2 == '1f' or yNotePos3 == '1f' or yNotePos4 == '1f' then
			nwcdraw.setFontClass('StaffSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*150*.01)
			local x1f, y1f = NoteHeads:xyTimeslot()
			nwcdraw.moveTo(x1f, y0+1)
			nwcdraw.setPen('solid',150)
			nwcdraw.line(x1f-0.25,y0+2.5,x1f+1.25,y0-0.5)
		end
		--SNARE Ghost Note
		if yNotePos1 == '1Y' or yNotePos2 == '1Y' or yNotePos3 == '1Y' or yNotePos4 == '1Y' then
			nwcdraw.setFontClass('StaffSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*125*.01)
			local x1Y, y1Y = NoteHeads:xyTimeslot()
			nwcdraw.moveTo(x1Y+0.55, y0+1)
			nwcdraw.alignText('baseline','center')
			nwcdraw.text('( )')
		end
		--HI-HAT Open
		if yNotePos1 == '5y' or yNotePos2 == '5y' or yNotePos3 == '5y' or yNotePos4 == '5y' then
			nwcdraw.setFontClass('StaffCueSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*100*.01)
			local x5y, y5y = NoteHeads:xyStemTip()
			nwcdraw.moveTo(x5y-0.45, y5y+1.5)
			nwcdraw.alignText('baseline','center')
			nwcdraw.text('')
		end
		--HI-HAT Closed
		if yNotePos1 == '5x' and t.HiHat or yNotePos2 == '5x' and t.HiHat or yNotePos3 == '5x' and t.HiHat or yNotePos4 == '5x' and t.HiHat then
			nwcdraw.setFontClass('StaffCueSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*100*.01)
			local x5x, y5x = NoteHeads:xyStemTip()
			nwcdraw.moveTo(x5x-0.45, y5x+1.5)
			nwcdraw.alignText('baseline','center')
			nwcdraw.text('+')
		end
		--HI-HAT Foot Splash
		if yNotePos1 == '-5z' or yNotePos2 == '-5z' or yNotePos3 == '-5z' or yNotePos4 == '-5z' then
			nwcdraw.setFontClass('StaffCueSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*100*.01)
			local x5z, y5z = NoteHeads:xyTimeslot()
			nwcdraw.moveTo(x5z+0.55, y0-5)
			nwcdraw.alignText('baseline','center')
			nwcdraw.text('g')
			nwcdraw.setFontClass('StaffSymbols')
			nwcdraw.moveTo(x5z+0.55, y0-5)
			nwcdraw.text('')
		end
		--CRASH
		if yNotePos1 == '6z' or yNotePos2 == '6z' or yNotePos3 == '6z' or yNotePos4 == '6z' then
			nwcdraw.setFontClass('StaffCueSymbols')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*100*.01)
			local x6z, y6z = NoteHeads:xyTimeslot()
			nwcdraw.moveTo(x6z+0.55, y0+6)
			nwcdraw.alignText('baseline','center')
			nwcdraw.text('g')
			nwcdraw.setFontClass('StaffSymbols')
			nwcdraw.moveTo(x6z+0.55, y0+6)
			nwcdraw.text('')
		end
	end
  end


--METRIC MODULATION--

  if t.Class=='Standard' and t.MetricMod and not t.Sticks then
	local T1 = t.T1:match('(%S+)')
	local T1Dot = t.T1:match('( Dotted)')
	local T2 = t.T2:match('(%S+)')
	local T2Dot = t.T2:match('( Dotted)')

	nwcdraw.alignText('baseline', 'left')
	
	nwcdraw.setFontClass('StaffSymbols')
	nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale1*.01)
	nwcdraw.text(symbols[T1])
	if T1Dot then
		nwcdraw.setFontClass('StaffCueSymbols')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale1*.01)
		nwcdraw.text('z')
	end

	nwcdraw.setFontClass('PageSmallText',3)
	nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale1*.01)
	if T1 == 'Eighth' then
		nwcdraw.text('  = ')
	else
		nwcdraw.text(' = ')
	end

	nwcdraw.setFontClass('StaffSymbols')
	nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale1*.01)
	nwcdraw.text(symbols[T2])
	if T2Dot then
		nwcdraw.setFontClass('StaffCueSymbols')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale1*.01)
		nwcdraw.text('z')
	end
  end


--STICKS--

--NO ICON
  if t.Class=='Standard' and t.Sticks and t.Icons == 'None' then 
		if t.label == '' then do end
		else
			nwcdraw.alignText('baseline','left')
			nwcdraw.setFontClass('PageSmallText')
			nwcdraw.setFontStyle('Bold Italic')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale3*.01)
			nwcdraw.text(t.label)
		end
  end

--STICKS ICON
  if t.Class=='Standard' and t.Sticks and t.Icons == 'Sticks' then 
		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*50/100*t.Scale2*.01)
		nwcdraw.moveTo((-0.5*t.Scale2)/100,(4.5*t.Scale2)/100)
		nwcdraw.text('',90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((-0.5*t.Scale2)/100,(4.5*t.Scale2)/100,(-0.5*t.Scale2)/100,0)

		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*50/100*t.Scale2*.01)
		nwcdraw.moveTo((0.5*t.Scale2)/100,0)
		nwcdraw.text('',90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((0.5*t.Scale2)/100,(4.5*t.Scale2)/100,(0.5*t.Scale2)/100,(0*t.Scale2)/100)

		if t.label == '' then do end
		else
			nwcdraw.moveTo((1.25*t.Scale2)/100,0)
			nwcdraw.alignText('baseline','left')
			nwcdraw.setFontClass('PageSmallText')
			nwcdraw.setFontStyle('Bold Italic')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale3*.01)
			nwcdraw.text('= '..t.label)
		end
  end

--BRUSHES Icon
  if t.Class=='Standard' and t.Sticks and t.Icons == 'Brushes' then 
		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((-0.5*t.Scale2)/100,(3.5*t.Scale2)/100)
		nwcdraw.text('',25)
		nwcdraw.text('',10)
		nwcdraw.text('',-10)
		nwcdraw.text('',-25)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((-0.5*t.Scale2)/100,(3.5*t.Scale2)/100,(-0.5*t.Scale2)/100,0)

		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((0.5*t.Scale2)/100,(1*t.Scale2)/100)
		nwcdraw.text('',25+180)
		nwcdraw.text('',10+180)
		nwcdraw.text('',-10+180)
		nwcdraw.text('',-25+180)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((0.5*t.Scale2)/100,(4.5*t.Scale2)/100,(0.5*t.Scale2)/100,(1*t.Scale2)/100)

		if t.label == '' then do end
		else
			nwcdraw.moveTo((1.25*t.Scale2)/100,0)
			nwcdraw.alignText('baseline','left')
			nwcdraw.setFontClass('PageSmallText')
			nwcdraw.setFontStyle('Bold Italic')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale3*.01)
			nwcdraw.text('= '..t.label)
		end
  end

--HARD MALLETS ICON
  if t.Class=='Standard' and t.Sticks and t.Icons == 'Hard Mallets' then 
		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((-0.5*t.Scale2)/100,(4.5*t.Scale2)/100)
		nwcdraw.text('',-90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((-0.5*t.Scale2)/100,(3.5*t.Scale2)/100,(-0.5*t.Scale2)/100,0)

		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((0.5*t.Scale2)/100,0)
		nwcdraw.text('',-90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((0.5*t.Scale2)/100,(4.5*t.Scale2)/100,(0.5*t.Scale2)/100,(1*t.Scale2)/100)

		if t.label == '' then do end
		else
			nwcdraw.moveTo((1.25*t.Scale2)/100,0)
			nwcdraw.alignText('baseline','left')
			nwcdraw.setFontClass('PageSmallText')
			nwcdraw.setFontStyle('Bold Italic')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale3*.01)
			nwcdraw.text('= '..t.label)
		end
  end

--SOFT MALLETS ICON
  if t.Class=='Standard' and t.Sticks and t.Icons == 'Soft Mallets' then 
		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((-0.5*t.Scale2)/100,(4.5*t.Scale2)/100)
		nwcdraw.text('',-90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((-0.5*t.Scale2)/100,(3.5*t.Scale2)/100,(-0.5*t.Scale2)/100,0)

		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((0.5*t.Scale2)/100,0)
		nwcdraw.text('',-90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((0.5*t.Scale2)/100,(4.5*t.Scale2)/100,(0.5*t.Scale2)/100,(1*t.Scale2)/100)

		if t.label == '' then do end
		else
			nwcdraw.moveTo((1.25*t.Scale2)/100,0)
			nwcdraw.alignText('baseline','left')
			nwcdraw.setFontClass('PageSmallText')
			nwcdraw.setFontStyle('Bold Italic')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale3*.01)
			nwcdraw.text('= '..t.label)
		end
  end

--MIXED MALLETS ICON
  if t.Class=='Standard' and t.Sticks and t.Icons == 'Mixed Mallets' then 
		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((-0.5*t.Scale2)/100,(4.5*t.Scale2)/100)
		nwcdraw.text('',-90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((-0.5*t.Scale2)/100,(3.5*t.Scale2)/100,(-0.5*t.Scale2)/100,0)

		nwcdraw.setFontClass('StaffSymbols')
		nwcdraw.alignText('baseline','center')
		nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale2*.01)
		nwcdraw.moveTo((0.5*t.Scale2)/100,0)
		nwcdraw.text('',-90)
		nwcdraw.setPen('solid',(200*t.Scale2)/100)
		nwcdraw.line((0.5*t.Scale2)/100,(4.5*t.Scale2)/100,(0.5*t.Scale2)/100,(1*t.Scale2)/100)

		if t.label == '' then do end
		else
			nwcdraw.moveTo((1.25*t.Scale2)/100,0)
			nwcdraw.alignText('baseline','left')
			nwcdraw.setFontClass('PageSmallText')
			nwcdraw.setFontStyle('Bold Italic')
			nwcdraw.setFontSize(nwcdraw.getFontSize()*t.Scale3*.01)
			nwcdraw.text('= '..t.label)
		end
  end

end


---------------------------------------------------------------------------------------------------


return {
	spec = object_spec,
	create = do_create,
	width = width,
	draw = do_draw,
}