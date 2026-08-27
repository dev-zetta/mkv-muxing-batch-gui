# Original upstream issue inventory

Snapshot date: 2026-08-27

## Sources and scope

This inventory was fetched from the GitHub REST API for
`yaser01/mkv-muxing-batch-gui` with `state=all`. Pull requests were removed
from the API response. The result is 121 issues: 56 open and 65 closed.

The original repository's last release and commit are 2.4.2 from January 2024.
Two descendants contain later work:

- `orphick/mkv-muxing-batch`: 2.7.1, ten commits ahead and zero behind the
  original main branch. It has focused regression tests, reproducible Windows
  packaging and pinned current dependencies. This is the adopted baseline.
- `Khaoklong51/mkv-muxing-batch-gui`: 3.0.0 beta on main and 3.0.1 on its
  testing branch. It is a larger refactor with useful fixes, but has no
  comparable automated test suite and is not a safe wholesale merge.

## Severity triage

Severity reflects data safety, false-success risk, crashes, and whether the core
batch workflow becomes unusable. Feature requests are not labeled as bugs.

### Critical and major issues addressed here

- **Critical — #156:** nonstandard process exits such as shell code 127 were
  treated as success. The queue now accepts only MKVToolNix codes 0 and 1,
  converts launch exceptions to failures, requires a non-empty expected output,
  calculates CRC from that output, and validates before overwrite finalization.
- **Critical — #146:** the maintained baseline coalesces CRC progress and avoids
  recursive queue traversal. Current Qt/Python testing exposed a second
  double-free during repeated queue shutdown; controller lifetime is now owned
  consistently and 100 repeated cycles pass.
- **Major — #128 and #166:** chapter removal was mutually exclusive with adding
  replacement chapters, and its command overwrote attachment removal. The
  response file now carries independent `--no-chapters` and
  `--no-attachments` options.
- **Major — #121:** an earlier Fast Mux choice leaked into later incompatible
  jobs. Ineligible jobs now explicitly reset `USE_MKVPROPEDIT`.
- **Major — #135 and #164:** Linux preferred an obsolete bundled MKVToolNix that
  no longer links on current distributions. Discovery now checks an explicit
  override, the user-local managed tools, PATH, and platform install locations
  before any working portable fallback. Linux users can use a current system
  package or the verified in-app publisher download.
- **Major — overwrite safety:** the old flow deleted the source before renaming
  the generated file. It now validates the generated output, atomically replaces
  an MKV source, and publishes a new-format MKV before removing a non-MKV source.

### Major issues still requiring work

- **#119, #123, #169 — release trust:** multiple malware reports concern old
  unsigned frozen executables. The adopted baseline adds reproducible packaging
  and SHA-256 manifests, but future Windows artifacts still need clean-builder
  provenance, signing, and independent malware scans.
- **#144 — zero-audio guard:** this is a valuable destructive-operation preflight
  and should be implemented before expanding format features.
- **#127 and #162 — multiple default/forced flags:** a candidate implementation
  exists in the Khaoklong testing branch, but it needs isolated tests against
  current Matroska semantics before integration.
- **#153 — network folders:** UNC/SMB support was previously claimed as fixed,
  but the newer report needs reproduction on current Windows and Linux paths.

### Minor bugs, usability reports, and support questions

- **#117** is a stale release-page link defect.
- **#165** is mainly discoverability: the two entries are the default favorites;
  more languages already exist in Settings.
- **#120** is a matching/empty-slot workflow limitation.
- **#137** is an extension-list omission, while #130 and #171 request non-Matroska
  output that `mkvmerge` does not produce.
- **#41** is partly addressed by subtitle-folder monitoring in 2.7.1.
- **#125 and #148** are addressed by 2.7.1 metadata title templates.

The remaining open reports are enhancements, support requests, or meta threads.
They should be prioritized after destructive-operation guards and real hardware/
filesystem reproductions.

## Complete issue snapshot

| Issue | State | Title | Updated |
|---|---|---|---|
| [#172](https://github.com/yaser01/mkv-muxing-batch-gui/issues/172) | open | add a feature to generate chapters by time | 2026-02-07 |
| [#171](https://github.com/yaser01/mkv-muxing-batch-gui/issues/171) | open | Can't export as mp4 or m4v### | 2025-11-06 |
| [#170](https://github.com/yaser01/mkv-muxing-batch-gui/issues/170) | open | FOR ANYONE LOOKING FOR UPDATES FOR THIS PROGRAM | 2025-12-19 |
| [#169](https://github.com/yaser01/mkv-muxing-batch-gui/issues/169) | open | Virus total scan | 2025-05-18 |
| [#168](https://github.com/yaser01/mkv-muxing-batch-gui/issues/168) | closed | 作者大大你好，能出一个简体中文的版本吗 | 2026-02-22 |
| [#167](https://github.com/yaser01/mkv-muxing-batch-gui/issues/167) | open | [FEATURE REQUEST] Only Keep Current Subtitles | 2025-05-17 |
| [#166](https://github.com/yaser01/mkv-muxing-batch-gui/issues/166) | open | Discard Old Chapters + Old Attachments not working correctly | 2025-02-25 |
| [#165](https://github.com/yaser01/mkv-muxing-batch-gui/issues/165) | open | selectable audio language is "English" and "Arabic" only | 2025-02-05 |
| [#164](https://github.com/yaser01/mkv-muxing-batch-gui/issues/164) | open | Linux Portable is Not Portable | 2025-05-16 |
| [#163](https://github.com/yaser01/mkv-muxing-batch-gui/issues/163) | open | FOR ANYONE POSTING REQUESTS OR BUGS : THE DEV ISN'T AROUND ANYMORE | 2024-11-28 |
| [#162](https://github.com/yaser01/mkv-muxing-batch-gui/issues/162) | open | Cannot flag multiple tracks as "Default" or "Forced". | 2024-09-24 |
| [#161](https://github.com/yaser01/mkv-muxing-batch-gui/issues/161) | open | [Feature Request] Select and Deselect All | 2024-09-14 |
| [#160](https://github.com/yaser01/mkv-muxing-batch-gui/issues/160) | open | [Feature Request] Fonts mux | 2024-09-14 |
| [#158](https://github.com/yaser01/mkv-muxing-batch-gui/issues/158) | open | Feature request: Option to leave a field empty | 2024-08-09 |
| [#157](https://github.com/yaser01/mkv-muxing-batch-gui/issues/157) | open | Folders and subfolders | 2024-09-10 |
| [#156](https://github.com/yaser01/mkv-muxing-batch-gui/issues/156) | open | Docker: The Program doesn't always mux "correctly", it just finishes every file within a second, but there's no files at the specified location. | 2024-07-28 |
| [#155](https://github.com/yaser01/mkv-muxing-batch-gui/issues/155) | open | Setting to move audio and/or subtitle to track 1 | 2024-07-30 |
| [#153](https://github.com/yaser01/mkv-muxing-batch-gui/issues/153) | open | [Feature request] Ability to work in Network attached Folders | 2024-06-26 |
| [#152](https://github.com/yaser01/mkv-muxing-batch-gui/issues/152) | open | [Feature request] Additional command line for mkvmerge | 2025-02-11 |
| [#151](https://github.com/yaser01/mkv-muxing-batch-gui/issues/151) | open | Can u make it where i can drag and drop ? | 2024-06-24 |
| [#150](https://github.com/yaser01/mkv-muxing-batch-gui/issues/150) | open | Please add flag | 2024-06-24 |
| [#149](https://github.com/yaser01/mkv-muxing-batch-gui/issues/149) | open | [Feature request] Fix bitstream timing info (when changing FPS) as a checkbox | 2024-06-20 |
| [#148](https://github.com/yaser01/mkv-muxing-batch-gui/issues/148) | open | Feature request | 2024-06-06 |
| [#147](https://github.com/yaser01/mkv-muxing-batch-gui/issues/147) | open | [Feature request] Auto multi-thread for single queue | 2024-06-05 |
| [#146](https://github.com/yaser01/mkv-muxing-batch-gui/issues/146) | open | [Bug] When processing large amounts of videos the GUI becomes unresponsive and no longer updates | 2024-06-04 |
| [#145](https://github.com/yaser01/mkv-muxing-batch-gui/issues/145) | open | [Feature Request] Skip queue items those unmodified, without generate new files of them. | 2024-06-04 |
| [#144](https://github.com/yaser01/mkv-muxing-batch-gui/issues/144) | open | [Feature Request] Option to prevent output zero audio track video files. | 2024-06-04 |
| [#143](https://github.com/yaser01/mkv-muxing-batch-gui/issues/143) | open | [Feature Request] Use indicated folder for relay/temp location for overwrite operations. | 2024-06-04 |
| [#142](https://github.com/yaser01/mkv-muxing-batch-gui/issues/142) | open | [Feature Request] Total changed size of processed files of current queue/session. | 2024-06-04 |
| [#141](https://github.com/yaser01/mkv-muxing-batch-gui/issues/141) | open | [Feature Request] Track order numbers as new sections on menu of [Only Keep those Audios/Subtitles] | 2024-06-04 |
| [#140](https://github.com/yaser01/mkv-muxing-batch-gui/issues/140) | open | [Feature Request] Enter or double click on Videos list entries to open files. | 2024-06-04 |
| [#139](https://github.com/yaser01/mkv-muxing-batch-gui/issues/139) | open | [Feature Request] Attach language to [Track Id] entries on the menu of [Only Keep Those Audios] | 2024-06-04 |
| [#138](https://github.com/yaser01/mkv-muxing-batch-gui/issues/138) | open | [Feature Request] Entries' size & format columns on menu of [Only Keep Those Subtitles] | 2024-06-04 |
| [#137](https://github.com/yaser01/mkv-muxing-batch-gui/issues/137) | open | Support for M2TS | 2024-05-26 |
| [#136](https://github.com/yaser01/mkv-muxing-batch-gui/issues/136) | open | An option to include subdirectories when selecting source folder | 2024-07-27 |
| [#135](https://github.com/yaser01/mkv-muxing-batch-gui/issues/135) | open | Run in Arch Linux not work | 2024-05-15 |
| [#134](https://github.com/yaser01/mkv-muxing-batch-gui/issues/134) | open | [Feature Request] pause resume processing in real time to temporary pause disk occupation. | 2024-05-10 |
| [#133](https://github.com/yaser01/mkv-muxing-batch-gui/issues/133) | open | [Feature Request] add items to queue while multiplexing process | 2024-05-21 |
| [#132](https://github.com/yaser01/mkv-muxing-batch-gui/issues/132) | open | [Feature Request] support legacy MIME types for font attachments | 2024-04-17 |
| [#130](https://github.com/yaser01/mkv-muxing-batch-gui/issues/130) | open | [REQUEST] Save video as original format | 2024-03-23 |
| [#129](https://github.com/yaser01/mkv-muxing-batch-gui/issues/129) | closed | App isn't opening | 2024-04-12 |
| [#128](https://github.com/yaser01/mkv-muxing-batch-gui/issues/128) | open | Discard Old Chapters not working | 2024-02-06 |
| [#127](https://github.com/yaser01/mkv-muxing-batch-gui/issues/127) | open | Only one subtitle track taggable as forced | 2024-02-07 |
| [#126](https://github.com/yaser01/mkv-muxing-batch-gui/issues/126) | open | [Feature Request] An Ability to Discard Tags and Global Tags | 2024-02-09 |
| [#125](https://github.com/yaser01/mkv-muxing-batch-gui/issues/125) | open | [Feature Request] An Ability to Change a File's Title | 2025-02-09 |
| [#123](https://github.com/yaser01/mkv-muxing-batch-gui/issues/123) | open | Windows Defender Detected (EXE) As Malware (Trojan:Win32/Phonzy.B!ml) | 2024-02-05 |
| [#122](https://github.com/yaser01/mkv-muxing-batch-gui/issues/122) | open | [Feature Request] An Ability to Search for a Language | 2024-02-09 |
| [#121](https://github.com/yaser01/mkv-muxing-batch-gui/issues/121) | open | The Program Seems to Be Confused After Doing MkvPropEdit | 2024-01-30 |
| [#120](https://github.com/yaser01/mkv-muxing-batch-gui/issues/120) | open | Fewer subtitles than videos | 2024-01-30 |
| [#119](https://github.com/yaser01/mkv-muxing-batch-gui/issues/119) | open | Trojan in Windows version 2.4.2 | 2024-01-24 |
| [#118](https://github.com/yaser01/mkv-muxing-batch-gui/issues/118) | open | Feature request: Set directories relative to source folder | 2024-01-22 |
| [#117](https://github.com/yaser01/mkv-muxing-batch-gui/issues/117) | open | Latest release link has a 33 added to the link for the 64bit qt6 version. Manually removing it downloads fine. | 2024-01-20 |
| [#115](https://github.com/yaser01/mkv-muxing-batch-gui/issues/115) | closed | Portable Windows QT6 is reported to be infected with Wacatac.B!ml by Windows Defender | 2024-01-19 |
| [#113](https://github.com/yaser01/mkv-muxing-batch-gui/issues/113) | closed | Virus/Malware Detection by Microsoft Defender? | 2024-01-16 |
| [#112](https://github.com/yaser01/mkv-muxing-batch-gui/issues/112) | closed | old attachments | 2024-01-19 |
| [#111](https://github.com/yaser01/mkv-muxing-batch-gui/issues/111) | open | Some feature requests | 2024-01-12 |
| [#107](https://github.com/yaser01/mkv-muxing-batch-gui/issues/107) | closed | Can't mux AV1 video format correctly | 2024-01-06 |
| [#106](https://github.com/yaser01/mkv-muxing-batch-gui/issues/106) | closed | Program doesn't work on Linux Mint (QT Platform Error) | 2024-01-09 |
| [#105](https://github.com/yaser01/mkv-muxing-batch-gui/issues/105) | closed | virus total flagged 32bit portable as trojan | 2024-01-06 |
| [#104](https://github.com/yaser01/mkv-muxing-batch-gui/issues/104) | closed | Destination path does not support CIFS path | 2024-01-06 |
| [#103](https://github.com/yaser01/mkv-muxing-batch-gui/issues/103) | closed | Feature request : recursive scan | 2024-05-23 |
| [#99](https://github.com/yaser01/mkv-muxing-batch-gui/issues/99) | open | Feature request (ability to mux video) | 2024-10-25 |
| [#98](https://github.com/yaser01/mkv-muxing-batch-gui/issues/98) | closed | Feature Request | 2024-01-06 |
| [#97](https://github.com/yaser01/mkv-muxing-batch-gui/issues/97) | open | [Request] please allow to export to same folder as input files | 2023-10-25 |
| [#94](https://github.com/yaser01/mkv-muxing-batch-gui/issues/94) | closed | "Remember last settings" or "setting-profiles" | 2024-02-23 |
| [#93](https://github.com/yaser01/mkv-muxing-batch-gui/issues/93) | closed | Processing recursive folders | 2023-06-15 |
| [#91](https://github.com/yaser01/mkv-muxing-batch-gui/issues/91) | closed | Bug in subtitle window | 2024-01-06 |
| [#90](https://github.com/yaser01/mkv-muxing-batch-gui/issues/90) | closed | Can't output to network share | 2024-01-06 |
| [#87](https://github.com/yaser01/mkv-muxing-batch-gui/issues/87) | closed | Changing video and audio names  | 2024-01-06 |
| [#85](https://github.com/yaser01/mkv-muxing-batch-gui/issues/85) | closed | Couldn’t run the linux version | 2024-01-07 |
| [#84](https://github.com/yaser01/mkv-muxing-batch-gui/issues/84) | closed | Some new features | 2024-01-06 |
| [#83](https://github.com/yaser01/mkv-muxing-batch-gui/issues/83) | closed | [Feature request] Set forced in mux settings window | 2023-05-09 |
| [#82](https://github.com/yaser01/mkv-muxing-batch-gui/issues/82) | closed | Can't drag to add files | 2023-02-27 |
| [#81](https://github.com/yaser01/mkv-muxing-batch-gui/issues/81) | closed | .mp4 files, not able to select discard certain tracks based on meta data (language) | 2024-01-19 |
| [#79](https://github.com/yaser01/mkv-muxing-batch-gui/issues/79) | closed | Request - Add Feature - Input->Subfolders ; Output -> Same As Source | 2024-01-06 |
| [#78](https://github.com/yaser01/mkv-muxing-batch-gui/issues/78) | closed | [Improvement] Please add support of the UNC path | 2024-01-06 |
| [#77](https://github.com/yaser01/mkv-muxing-batch-gui/issues/77) | closed | Feature request - change framerate | 2024-01-06 |
| [#76](https://github.com/yaser01/mkv-muxing-batch-gui/issues/76) | closed | Feature Request | 2024-01-06 |
| [#74](https://github.com/yaser01/mkv-muxing-batch-gui/issues/74) | closed | eac3 support | 2023-01-09 |
| [#72](https://github.com/yaser01/mkv-muxing-batch-gui/issues/72) | closed | how to remove track name | 2024-01-06 |
| [#70](https://github.com/yaser01/mkv-muxing-batch-gui/issues/70) | closed | Feature request | 2024-01-06 |
| [#68](https://github.com/yaser01/mkv-muxing-batch-gui/issues/68) | closed | installation in the default mka program for audio and the inability to drag a file from explorer into the program | 2023-05-08 |
| [#67](https://github.com/yaser01/mkv-muxing-batch-gui/issues/67) | closed | Feature request: support adding forced subtitle in addition to non-forced subtitle to video | 2023-05-12 |
| [#66](https://github.com/yaser01/mkv-muxing-batch-gui/issues/66) | closed | Dysfunctional files and pre-checks | 2022-10-26 |
| [#64](https://github.com/yaser01/mkv-muxing-batch-gui/issues/64) | closed | Delete option | 2022-09-24 |
| [#63](https://github.com/yaser01/mkv-muxing-batch-gui/issues/63) | closed | Dark Theme | 2024-01-06 |
| [#62](https://github.com/yaser01/mkv-muxing-batch-gui/issues/62) | closed | Removing Video to get MKA files | 2022-09-25 |
| [#61](https://github.com/yaser01/mkv-muxing-batch-gui/issues/61) | closed | [Help] Is there a way to launch mkv-muxing-batch-gui in MacOS | 2022-09-28 |
| [#59](https://github.com/yaser01/mkv-muxing-batch-gui/issues/59) | closed | Missing Files MkvMerge File | 2023-05-08 |
| [#58](https://github.com/yaser01/mkv-muxing-batch-gui/issues/58) | closed | Req: Don't duplicate existing attachments | 2024-01-06 |
| [#57](https://github.com/yaser01/mkv-muxing-batch-gui/issues/57) | closed | Thumbnail option | 2024-01-06 |
| [#56](https://github.com/yaser01/mkv-muxing-batch-gui/issues/56) | closed | issue | 2022-09-23 |
| [#55](https://github.com/yaser01/mkv-muxing-batch-gui/issues/55) | open | Request: Auto-detect languages | 2023-05-14 |
| [#54](https://github.com/yaser01/mkv-muxing-batch-gui/issues/54) | closed | [Feature Request] Just some suggestions | 2024-01-19 |
| [#53](https://github.com/yaser01/mkv-muxing-batch-gui/issues/53) | closed | Change order of existing tracks | 2024-01-07 |
| [#52](https://github.com/yaser01/mkv-muxing-batch-gui/issues/52) | closed | Allow Source Folder from Network Drive | 2022-09-23 |
| [#51](https://github.com/yaser01/mkv-muxing-batch-gui/issues/51) | closed | Feature request : Multi-Folder File Font Attachments | 2024-01-06 |
| [#49](https://github.com/yaser01/mkv-muxing-batch-gui/issues/49) | closed | Feature request : make an option to overwrite source files when starting the batch | 2024-01-21 |
| [#48](https://github.com/yaser01/mkv-muxing-batch-gui/issues/48) | closed | new issue | 2022-05-05 |
| [#47](https://github.com/yaser01/mkv-muxing-batch-gui/issues/47) | closed | Cannot run on Linux | 2022-05-04 |
| [#46](https://github.com/yaser01/mkv-muxing-batch-gui/issues/46) | closed | Only English or Arabic for language | 2022-05-03 |
| [#41](https://github.com/yaser01/mkv-muxing-batch-gui/issues/41) | open | QoL improvements | 2022-05-07 |
| [#40](https://github.com/yaser01/mkv-muxing-batch-gui/issues/40) | closed | Delay with eac3to | 2022-05-03 |
| [#39](https://github.com/yaser01/mkv-muxing-batch-gui/issues/39) | closed | Ability to remove title and track names | 2022-05-01 |
| [#38](https://github.com/yaser01/mkv-muxing-batch-gui/issues/38) | closed | Default Subtitle | 2022-03-20 |
| [#36](https://github.com/yaser01/mkv-muxing-batch-gui/issues/36) | closed | Using installed mvkmerge.exe and mkvpropedit.exe instead of supplied one | 2022-05-01 |
| [#35](https://github.com/yaser01/mkv-muxing-batch-gui/issues/35) | closed | Give more options for keep/default subs (other than just lang or track#) | 2022-05-01 |
| [#34](https://github.com/yaser01/mkv-muxing-batch-gui/issues/34) | closed | OPUS support | 2022-05-01 |
| [#33](https://github.com/yaser01/mkv-muxing-batch-gui/issues/33) | closed | Option to not keep chapters | 2022-05-01 |
| [#23](https://github.com/yaser01/mkv-muxing-batch-gui/issues/23) | closed | Add .ts support | 2022-05-01 |
| [#22](https://github.com/yaser01/mkv-muxing-batch-gui/issues/22) | open | Adding files to queue without waiting the muxing to finish | 2022-05-01 |
| [#21](https://github.com/yaser01/mkv-muxing-batch-gui/issues/21) | closed | Settings are stored in \AppData\Local\Temp only? | 2022-05-01 |
| [#19](https://github.com/yaser01/mkv-muxing-batch-gui/issues/19) | closed | Issue with Subtitle #2 | 2021-10-21 |
| [#16](https://github.com/yaser01/mkv-muxing-batch-gui/issues/16) | closed | 2.0 contains trojan? | 2021-10-15 |
| [#10](https://github.com/yaser01/mkv-muxing-batch-gui/issues/10) | closed | [Feature Request] Default Directories for Episodes, Subtitles and Output already set at the start of the program. | 2021-10-10 |
| [#9](https://github.com/yaser01/mkv-muxing-batch-gui/issues/9) | closed | [Feature Request] multi folder support and queue enhancement | 2021-10-10 |
| [#5](https://github.com/yaser01/mkv-muxing-batch-gui/issues/5) | closed | Feature for Audio | 2021-10-10 |
| [#4](https://github.com/yaser01/mkv-muxing-batch-gui/issues/4) | closed | Feature for Video | 2021-10-10 |
| [#3](https://github.com/yaser01/mkv-muxing-batch-gui/issues/3) | closed | Problem in choose subtitles tracks | 2021-10-11 |
| [#2](https://github.com/yaser01/mkv-muxing-batch-gui/issues/2) | closed | request a feature for tracks | 2021-10-10 |
| [#1](https://github.com/yaser01/mkv-muxing-batch-gui/issues/1) | closed | Asking for a feature | 2021-10-10 |
