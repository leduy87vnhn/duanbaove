# Hướng dẫn nhúng Stream vào Windows Application

## Stream URL
Sau khi server chạy và stream được start, bạn sẽ có URL:
```
http://localhost:8503/hls/stream.m3u8
```

Hoặc từ máy khác trong mạng:
```
http://<IP_SERVER>:8503/hls/stream.m3u8
```

## 1. Windows Forms / WPF Application với VLC

### Sử dụng LibVLCSharp (.NET)

#### Cài đặt NuGet Packages:
```powershell
Install-Package LibVLCSharp
Install-Package LibVLCSharp.WPF
Install-Package VideoLAN.LibVLC.Windows
```

#### Code mẫu (WPF):
```csharp
using LibVLCSharp.Shared;
using LibVLCSharp.WPF;
using System;
using System.Windows;

namespace VideoMonitorApp
{
    public partial class MainWindow : Window
    {
        private LibVLC _libVLC;
        private MediaPlayer _mediaPlayer;
        private const string STREAM_URL = "http://192.168.1.100:8503/hls/stream.m3u8";

        public MainWindow()
        {
            InitializeComponent();
            InitializeVLC();
        }

        private void InitializeVLC()
        {
            Core.Initialize();
            
            _libVLC = new LibVLC(new string[] {
                "--network-caching=2000",      // 2s cache
                "--clock-jitter=0",
                "--clock-synchro=0"
            });
            
            _mediaPlayer = new MediaPlayer(_libVLC);
            
            // Gắn vào VideoView control trong XAML
            videoView.MediaPlayer = _mediaPlayer;
        }

        private void ButtonStart_Click(object sender, RoutedEventArgs e)
        {
            // Start stream trên server trước
            StartStreamOnServer();
            
            // Đợi 3 giây cho segments được tạo
            Task.Delay(3000).ContinueWith(t =>
            {
                Dispatcher.Invoke(() =>
                {
                    var media = new Media(_libVLC, STREAM_URL, FromType.FromLocation);
                    _mediaPlayer.Play(media);
                });
            });
        }

        private async void StartStreamOnServer()
        {
            using (var client = new HttpClient())
            {
                await client.PostAsync("http://192.168.1.100:8503/api/stream/start", null);
            }
        }

        private void ButtonStop_Click(object sender, RoutedEventArgs e)
        {
            _mediaPlayer?.Stop();
        }

        protected override void OnClosed(EventArgs e)
        {
            _mediaPlayer?.Dispose();
            _libVLC?.Dispose();
            base.OnClosed(e);
        }
    }
}
```

#### XAML:
```xml
<Window x:Class="VideoMonitorApp.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:vlc="clr-namespace:LibVLCSharp.WPF;assembly=LibVLCSharp.WPF"
        Title="Video Monitor" Height="600" Width="800">
    <Grid>
        <Grid.RowDefinitions>
            <RowDefinition Height="*"/>
            <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>
        
        <vlc:VideoView x:Name="videoView" Grid.Row="0"/>
        
        <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="10">
            <Button x:Name="ButtonStart" Content="▶ Start" 
                    Width="100" Height="35" Margin="5" 
                    Click="ButtonStart_Click"/>
            <Button x:Name="ButtonStop" Content="⏹ Stop" 
                    Width="100" Height="35" Margin="5" 
                    Click="ButtonStop_Click"/>
        </StackPanel>
    </Grid>
</Window>
```

## 2. Windows Forms với Vlc.DotNet

#### Cài đặt NuGet:
```powershell
Install-Package Vlc.DotNet.Forms
```

#### Code mẫu:
```csharp
using Vlc.DotNet.Forms;
using System;
using System.Windows.Forms;
using System.IO;

namespace VideoMonitorWinForms
{
    public partial class Form1 : Form
    {
        private VlcControl vlcControl;
        private const string STREAM_URL = "http://192.168.1.100:8503/hls/stream.m3u8";
        
        public Form1()
        {
            InitializeComponent();
            InitializeVlc();
        }

        private void InitializeVlc()
        {
            var currentDirectory = Path.GetDirectoryName(Application.ExecutablePath);
            var vlcLibDirectory = new DirectoryInfo(Path.Combine(currentDirectory, "libvlc", 
                IntPtr.Size == 4 ? "win-x86" : "win-x64"));

            vlcControl = new VlcControl();
            vlcControl.VlcLibDirectory = vlcLibDirectory;
            vlcControl.Dock = DockStyle.Fill;
            
            // Add options for better streaming
            vlcControl.VlcMediaplayerOptions = new[]
            {
                "--network-caching=2000",
                "--clock-jitter=0"
            };
            
            this.Controls.Add(vlcControl);
        }

        private async void ButtonPlay_Click(object sender, EventArgs e)
        {
            // Start stream on server
            using (var client = new HttpClient())
            {
                await client.PostAsync("http://192.168.1.100:8503/api/stream/start", null);
            }
            
            // Wait for segments
            await Task.Delay(3000);
            
            // Play
            vlcControl.Play(new Uri(STREAM_URL));
        }

        private void ButtonStop_Click(object sender, EventArgs e)
        {
            vlcControl.Stop();
        }
    }
}
```

## 3. Electron App (Windows Desktop)

#### package.json:
```json
{
  "dependencies": {
    "electron": "^28.0.0",
    "hls.js": "^1.5.15"
  }
}
```

#### main.js:
```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(createWindow);
```

#### index.html:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Video Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body { margin: 0; background: #000; }
        video { width: 100%; height: 100vh; }
        .controls { 
            position: fixed; 
            bottom: 20px; 
            left: 50%; 
            transform: translateX(-50%);
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            margin: 5px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <video id="video" controls></video>
    <div class="controls">
        <button onclick="startStream()">▶ Start</button>
        <button onclick="stopStream()">⏹ Stop</button>
    </div>

    <script>
        const video = document.getElementById('video');
        const STREAM_URL = 'http://192.168.1.100:8503/hls/stream.m3u8';
        let hls;

        async function startStream() {
            // Start on server
            await fetch('http://192.168.1.100:8503/api/stream/start', {
                method: 'POST'
            });

            // Wait for segments
            setTimeout(() => {
                if (Hls.isSupported()) {
                    hls = new Hls({
                        maxBufferLength: 30,
                        maxMaxBufferLength: 60
                    });
                    hls.loadSource(STREAM_URL);
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MANIFEST_PARSED, () => {
                        video.play();
                    });
                }
            }, 3000);
        }

        function stopStream() {
            if (hls) {
                hls.destroy();
                video.pause();
            }
            fetch('http://192.168.1.100:8503/api/stream/stop', {
                method: 'POST'
            });
        }
    </script>
</body>
</html>
```

## 4. C++ Application với libVLC

```cpp
#include <vlc/vlc.h>
#include <windows.h>

class VideoPlayer {
private:
    libvlc_instance_t* vlcInstance;
    libvlc_media_player_t* mediaPlayer;
    
public:
    VideoPlayer() {
        const char* args[] = {
            "--network-caching=2000",
            "--clock-jitter=0"
        };
        
        vlcInstance = libvlc_new(sizeof(args) / sizeof(args[0]), args);
        mediaPlayer = libvlc_media_player_new(vlcInstance);
    }
    
    void Play(const char* url, HWND hwnd) {
        libvlc_media_t* media = libvlc_media_new_location(vlcInstance, url);
        libvlc_media_player_set_media(mediaPlayer, media);
        libvlc_media_player_set_hwnd(mediaPlayer, hwnd);
        libvlc_media_player_play(mediaPlayer);
        libvlc_media_release(media);
    }
    
    void Stop() {
        libvlc_media_player_stop(mediaPlayer);
    }
    
    ~VideoPlayer() {
        libvlc_media_player_release(mediaPlayer);
        libvlc_release(vlcInstance);
    }
};

// Usage
VideoPlayer player;
player.Play("http://192.168.1.100:8503/hls/stream.m3u8", hwndVideo);
```

## 5. Python Application (Tkinter/PyQt)

```python
import vlc
import tkinter as tk
from tkinter import ttk
import requests

class VideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Monitor")
        
        # VLC instance
        self.instance = vlc.Instance([
            '--network-caching=2000',
            '--clock-jitter=0'
        ])
        self.player = self.instance.media_player_new()
        
        # UI
        self.video_frame = tk.Frame(root, bg='black')
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="▶ Start", command=self.start).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⏹ Stop", command=self.stop).pack(side=tk.LEFT, padx=5)
        
        # Set window handle
        self.player.set_hwnd(self.video_frame.winfo_id())
    
    def start(self):
        # Start stream on server
        requests.post('http://192.168.1.100:8503/api/stream/start')
        
        # Wait and play
        self.root.after(3000, self._play)
    
    def _play(self):
        media = self.instance.media_new('http://192.168.1.100:8503/hls/stream.m3u8')
        self.player.set_media(media)
        self.player.play()
    
    def stop(self):
        self.player.stop()
        requests.post('http://192.168.1.100:8503/api/stream/stop')

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('1024x768')
    app = VideoApp(root)
    root.mainloop()
```

## Lưu ý quan trọng:

### 1. **Địa chỉ IP Server**
Thay `192.168.1.100` bằng IP thực tế của server:
```bash
# Xem IP của server
ipconfig
```

### 2. **Firewall**
Mở port 8503 trên server:
```powershell
# PowerShell (Run as Administrator)
New-NetFirewallRule -DisplayName "Stream Server" -Direction Inbound -LocalPort 8503 -Protocol TCP -Action Allow
```

### 3. **Network Caching**
- Tăng `network-caching` nếu mạng chậm (3000-5000ms)
- Giảm nếu muốn độ trễ thấp hơn (1000ms)

### 4. **Sequence khởi động**
```
1. Start server: npm start
2. Call API: POST /api/stream/start
3. Đợi 3-5 giây cho segments được tạo
4. Play stream: http://IP:8503/hls/stream.m3u8
```

### 5. **Testing Stream**
Test bằng VLC Media Player trước:
```
1. Mở VLC
2. Media > Open Network Stream
3. Nhập: http://IP:8503/hls/stream.m3u8
4. Play
```

## Ưu điểm HLS cho Windows App:

✅ **Cross-platform**: Chạy trên mọi nền tảng  
✅ **Buffering tốt**: Giảm lag khi mạng yếu  
✅ **HTTP-based**: Dễ đi qua firewall  
✅ **Adaptive**: Có thể tự động điều chỉnh chất lượng  
✅ **Reliable**: VLC, FFmpeg hỗ trợ native  

## API Endpoints cho Windows App:

```
POST /api/stream/start    - Bắt đầu stream
POST /api/stream/stop     - Dừng stream  
GET  /api/stream/status   - Kiểm tra trạng thái
GET  /hls/stream.m3u8     - Playlist file (link để play)
```
