-- found here: https://www.macscripter.net/t/writing-list-our-to-csv-file/72908
on listToCSV(theList, separator)
	copy theList to theList -- Use a copy in case the original needs to be preserved.
	set astid to AppleScript's text item delimiters
	set AppleScript's text item delimiters to separator
	-- Check each item in each sublist of the input list.
	repeat with thisSublist in theList
		repeat with thisField in thisSublist
			-- Make sure we have a text version of the item (assuming this is possible!).
			set fieldValue to thisField as text
			if (fieldValue contains quote) then
				-- If the value contains double-quote(s), escape them and enquote it.
				set AppleScript's text item delimiters to quote
				set textItems to fieldValue's text items
				set AppleScript's text item delimiters to "\"\""
				set thisField's contents to quote & textItems & quote
				set AppleScript's text item delimiters to separator
			else if ((fieldValue contains separator) or ((count fieldValue's paragraphs) > 1)) then
				-- Enquote the value if it contains the separator or a line ending.
				set thisField's contents to quote & fieldValue & quote
			end if
		end repeat
		-- Replace the entire sublist with text formed from its values joined with the separator.
		set thisSublist's contents to thisSublist as text
	end repeat
	-- Combine the sublist replacements into a single text with linefeeds between them.
	set AppleScript's text item delimiters to linefeed
	set CSVText to theList as text
	set AppleScript's text item delimiters to astid

	return CSVText
end listToCSV

-- based on this: https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/ReadandWriteFiles.html#//apple_ref/doc/uid/TP40016239-CH58-SW1
on writeDataToFile(theData, theFile, overwriteExistingContent)
	try
		set theFile to theFile as string
		set openedFile to open for access file theFile with write permission

		if overwriteExistingContent is true then set eof of openedFile to 0

		write theData to openedFile starting at eof as Çclass utf8È
		close access openedFile
		return true
	on error
		try
			close access file theFile
		end try

		return false
	end try
end writeDataToFile


-- eventually try for track_num, duration_in_secs
set csvHeaders to {"persistent_id", "track_number", "track_name", "track_artist", "album", "album_artist", "track_year", "last_played", "play_count", "cloud_status", "location"}
set listenData to {}
set beginning of listenData to csvHeaders

tell application "Music"
    --set lib to library playlist 1
	repeat with currTrk in file tracks
		set track_name to name of currTrk
		set albumArtist to album artist of currTrk
		set track_artist to artist of currTrk
		set last_played to played date of currTrk
		set playCnt to played count of currTrk
		set albumName to album of currTrk
		set trackNum to track number of currTrk
		set cloudStatus to cloud status of currTrk
		set loc to location of currTrk
		set persistentId to persistent ID of currTrk
		set yr to year of currTrk
		set end of listenData to {persistentId as text, trackNum as text, track_name as text, track_artist as text, albumName as text, albumArtist as text, yr as text, last_played as text, playCnt as text, cloudStatus as text, loc as text }
	end repeat
end tell
--set display to listToCSV(listenData, ",")

-- NOTE the file must exist! Eventually set up to create file if not exists.
set dataFile to ((path to home folder) as text) & "Code:Data:Music:libraryFiles.csv"
writeDataToFile(listToCSV(listenData, ","), dataFile, true)
