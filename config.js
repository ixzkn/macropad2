{
	// Location of foobar text output file:
	playingFile: "M:\\now_playing.txt",
	// File is expected to have one entry per line, this says what is on each line:
	fileFormat: ["playing","artist","title","album","rating","percent","art","greater4"],
	// Executable location:
	playerExe: "C:\\Program Files (x86)\\foobar2000\\foobar2000.exe",
	// USB bus id:
	deviceId: "USB\\VID_1B4F&PID_9204&MI_00\\",
	// Only used in rare cases WMI cant figure out the device:
	defaultPort: "COM18",
	// Configured baud rate (must match Arduino code):
	baudRate: 115200
}
