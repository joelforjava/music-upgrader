# Music Upgrader

The purpose of this project is to allow me to upgrade my iTunes/Apple Music library files, using several Beets
collections as the source for the new files. I still have a large digital music collection of MP3s, FLACs, and ALAC files,
in addition to the songs I buy from the iTunes store. The non-iTunes files are of varying degrees of quality, from
192kbps MP3s to lossless ALAC. Many of the MP3s have since been re-ripped to either 320kbps MP3 files or FLAC. Updating
Apple Music to use these new files can be a bit cumbersome if you work straight from the GUI.  If you use AppleScript,
the amount of time can be reduced quite a bit, but AppleScript can also be a bit verbose to work with, at least to me.
I am far more at ease with Python or Java.

I have seen several scripts that can get close to the functionality I want, but none of them can get me all the way
there, which I expect. I am guessing my use case might help a handful of people, at best.

I originally intended to write all of this in JavaScript, utilizing the JXA framework instead of AppleScript. However,
in initial testing, the JXA just didn't work. It would throw an exception where the original AppleScript was fine.
Perhaps I'm just a bit more rusty at Javascript than I realize. Either way, I wasn't getting it to work.

Therefore, the orchestrating part of this is written in Python, with interfaces to AppleScript and to the Beets music manager.
As mentioned above, Beets has the newer versions of all my files.

## Running

The collection of the data is largely automated. You start with the main 'library' csv file for the first step, `check-upgrade`,
which is generated via the `scripts/load_all.applescript` script. If the file names in iTunes matched those in
Beets, the whole thing probably could've been automated to perform all the steps. However, there are differences in
track names between the two systems that will require my manual intervention.

Examples of this include the following "Construction of the Masses Pt. 1" vs. "Construction of the Masses, Part 1" or
"Now That's Rock 'N Roll" vs. "Now That's Rock-n-Roll". You could probably tokenize the titles and use a bit of text
replacement to try and get these right without manual overrides, but I honestly didn't want to bother with that. The
best I did was use some basic regex to handle the different characters used for apostrophes.

That works for me and gives me a bit more control over how the files are handled throughout the process. It lets me
subdivide the albums so that I can process a few at a time, and also let me update how the year used in the iTunes/Music
track is handled. For a lot of my files, the tracks in iTunes have the track release year as the file's year value. For
example, if we're looking at the "Big Ones" compilation from Aerosmith that was released in 1994, only the previously
unreleased tracks retain 1994 as their year. Tracks from previous releases get the years associated with the album of
original release. This helps me to build accurate year and decade playlists, so if I want an all 2000s playlist,
you won't see any of the "The Definitive Collection" or "Essential" releases or that came out during the mid-2000s.

Of course, that takes a lot of time and not all albums have had this update applied, so my Beets database has
a lot of the later albums with their "original_year" value set to their original year, similar to how "Big Ones" above
was updated. With the `yearfixer` plugin, it was a lot easier to get Beets' data updated. And now with this, I could
read the data back from iTunes if I wanted to and save it back to Beets. That functionality doesn't currently exist,
but it should be doable.

My point is, breaking the steps up allows me to better control the output and recover from any failures before moving
to the next step.


## Steps

The steps should be followed in this order

* load-itunes
  * Load the latest library values from iTunes
* check-upgrade
  * Determine which files from iTunes can be upgraded to a higher quality file
  * Files that can be upgraded are placed in one file
    * `upgrade_checks_*.csv`
    * Can update this file to control the `year` value that is used during the `convert-files` step
      * Defaults to `itunes_year`
      * Other values: `b_year`, `b_original_year`, with `b_original_year` being the likely alternative
  * Those that cannot be upgraded are placed in a separate file
    * `no_upgrade_*.csv`
    * This will allow manual verification
    * Can then update the `libraryFiles.csv` file with updated names so that they can pass another check
* convert-files
  * Uses the `upgrade_checks_*.csv` file as input
  * Convert FLAC as ALAC to staging
    * Allows for updating tags, e.g. adding `Rating` for Explicit tags
  * Copy MP3 to staging
* copy-files
  * Copy files to final library location, e.g. `~/Music/Music`
* apply-updates
  * Update iTunes with the file locations as they were placed from the `copy-files` step

