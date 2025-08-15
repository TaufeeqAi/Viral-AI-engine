import 'package:cyrene_ui/services/voice_service.dart';
import 'package:flutter/material.dart';

class VoiceChatScreen extends StatefulWidget {
  final String agentId;
  const VoiceChatScreen({required this.agentId});

  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

class _VoiceChatScreenState extends State<VoiceChatScreen> {
  // final voiceService = VoiceService();
  bool isRecording = false;

  // @override
  // void initState() {
  //   super.initState();
  //   voiceService.init(widget.agentId);
  // }

  // void _toggleRecording() async {
  //   if (isRecording) {
  //     await voiceService.stop();
  //   } else {
  //     await voiceService.startSendingAudio();
  //   }
  //   setState(() => isRecording = !isRecording);
  // }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Voice Chat")),
      body: Center(
        child: IconButton(
          icon: Icon(isRecording ? Icons.stop : Icons.mic),
          onPressed: () => print("_toggleRecording needs to be implmented"),
          iconSize: 80,
          color: isRecording ? Colors.red : Colors.blue,
        ),
      ),
    );
  }
}
