// import 'dart:typed_data';
// import 'package:web_socket_channel/web_socket_channel.dart';
// import 'package:flutter_sound/flutter_sound.dart';

// class VoiceService {
//   final _recorder = FlutterSoundRecorder();
//   final _player = FlutterSoundPlayer();
//   late WebSocketChannel _channel;

//   Future<void> init(String agentId) async {
//     await _recorder.openRecorder();
//     await _player.openPlayer();
//     _channel = WebSocketChannel.connect(
//       Uri.parse('ws://localhost:8002/ws/chat/voice/$agentId'),
//     );

//     // Audio response stream from server
//     _channel.stream.listen((data) async {
//       await _player.startPlayerFromStream();
//       _player.foodSink!.add(Uint8List.fromList(data));
//     });
//   }

//   Future<void> startSendingAudio() async {
//     await _recorder.startRecorder(
//       codec: Codec.pcm16,
//       sampleRate: 16000,
//       bitRate: 16000,
//       toStream: _channel.sink.add,
//     );
//   }

//   Future<void> stop() async {
//     await _recorder.stopRecorder();
//     await _player.stopPlayer();
//     await _recorder.closeRecorder();
//     await _player.closePlayer();
//     _channel.sink.close();
//   }
// }
