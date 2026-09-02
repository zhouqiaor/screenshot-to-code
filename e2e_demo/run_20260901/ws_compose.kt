import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                SettingsScreen()
            }
        }
    }
}

@Composable
fun SettingsScreen() {
    // Background gradient simulating mountain sunset
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF1a3a6b),
                        Color(0xFF2d5a8a),
                        Color(0xFF4a6fa5),
                        Color(0xFFc47a3a),
                        Color(0xFF8b4513)
                    )
                )
            )
    ) {
        // Top status bar
        TopStatusBar()

        // 投屏码 title
        Text(
            text = "投屏码",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 100.dp)
        )

        // Main settings window
        Surface(
            modifier = Modifier
                .width(800.dp)
                .height(520.dp)
                .align(Alignment.Center),
            shape = RoundedCornerShape(12.dp),
            color = Color(0xFFf5f5f7),
            shadowElevation = 8.dp
        ) {
            Row(modifier = Modifier.fillMaxSize()) {
                // Left sidebar
                LeftSidebar()

                // Vertical divider
                Divider(
                    modifier = Modifier
                        .width(1.dp)
                        .fillMaxHeight(),
                    color = Color(0xFFe0e0e0)
                )

                // Right content area
                RightContent()
            }
        }

        // Page indicator dots
        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 100.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(Color(0xFFaaaaaa), shape = RoundedCornerShape(4.dp))
            )
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .width(24.dp)
                    .background(Color.White, shape = RoundedCornerShape(4.dp))
            )
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(Color(0xFFaaaaaa), shape = RoundedCornerShape(4.dp))
            )
        }

        // Bottom bar
        BottomBar()
    }
}

@Composable
fun TopStatusBar() {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        color = Color.Transparent
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                color = Color(0xCC222222),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "NJRC-PAOE",
                        color = Color.White,
                        fontSize = 14.sp
                    )
                    Text(
                        text = "|",
                        color = Color.White,
                        fontSize = 14.sp
                    )
                    Icon(
                        imageVector = Icons.Default.MicOff,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(16.dp)
                    )
                    Icon(
                        imageVector = Icons.Default.Cast,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "16:55",
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

@Composable
fun LeftSidebar() {
    var selectedItem by remember { mutableStateOf(1) }

    Column(
        modifier = Modifier
            .width(320.dp)
            .fillMaxHeight()
            .background(Color(0xFFf5f5f7))
            .padding(16.dp)
    ) {
        // Settings title
        Text(
            text = "设置",
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF222222),
            modifier = Modifier.padding(bottom = 16.dp, start = 4.dp)
        )

        // Search bar
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .height(40.dp),
            color = Color.White,
            shape = RoundedCornerShape(20.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    tint = Color(0xFF999999),
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "搜索设置项",
                    color = Color(0xFF999999),
                    fontSize = 14.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Menu items
        MenuItem(
            icon = Icons.Default.Apartment,
            iconBgColor = Color(0xFF217aff),
            title = "企业服务配置",
            hasBadge = true,
            hasArrow = true,
            isSelected = selectedItem == 0,
            onClick = { selectedItem = 0 }
        )

        MenuItem(
            icon = Icons.Default.VolumeUp,
            iconBgColor = Color(0xFF6c5ce7),
            title = "声音与显示",
            hasArrow = true,
            isSelected = selectedItem == 1,
            onClick = { selectedItem = 1 }
        )

        MenuItem(
            icon = Icons.Default.Videocam,
            iconBgColor = Color(0xFFf39c12),
            title = "摄像机",
            status = "已开启",
            hasArrow = true,
            isSelected = selectedItem == 2,
            onClick = { selectedItem = 2 }
        )

        MenuItem(
            icon = Icons.Default.Wallpaper,
            iconBgColor = Color(0xFF27ae60),
            title = "壁纸",
            hasArrow = true,
            isSelected = selectedItem == 3,
            onClick = { selectedItem = 3 }
        )

        MenuItem(
            icon = Icons.Default.Wifi,
            iconBgColor = Color(0xFF3498db),
            title = "Wi-Fi",
            status = "未连接",
            hasArrow = true,
            isSelected = selectedItem == 4,
            onClick = { selectedItem = 4 }
        )

        MenuItem(
            icon = Icons.Default.AutoAwesome,
            iconBgColor = Color(0xFF1abc9c),
            title = "智慧功能",
            hasArrow = true,
            isSelected = selectedItem == 5,
            onClick = { selectedItem = 5 }
        )

        MenuItem(
            icon = Icons.Default.Tune,
            iconBgColor = Color(0xFF27ae60),
            title = "高级设置",
            hasArrow = true,
            isSelected = selectedItem == 6,
            onClick = { selectedItem = 6 }
        )
    }
}

@Composable
fun MenuItem(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    iconBgColor: Color,
    title: String,
    status: String? = null,
    hasBadge: Boolean = false,
    hasArrow: Boolean = false,
    isSelected: Boolean = false,
    onClick: () -> Unit = {}
) {
    val bgColor = if (isSelected) Color(0xFFe8edff) else Color.Transparent
    val textColor = if (isSelected) Color(0xFF217aff) else Color(0xFF333333)

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        color = bgColor,
        shape = RoundedCornerShape(8.dp),
        onClick = onClick
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Icon circle
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .background(iconBgColor, shape = RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(16.dp)
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            // Title
            Text(
                text = title,
                color = textColor,
                fontSize = 14.sp,
                fontWeight = if (isSelected) FontWeight.Medium else FontWeight.Normal,
                modifier = Modifier.weight(1f)
            )

            // Badge
            if (hasBadge) {
                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .background(Color.Red, shape = RoundedCornerShape(3.dp))
                )
                Spacer(modifier = Modifier.width(4.dp))
            }

            // Status
            if (status != null) {
                Text(
                    text = status,
                    color = Color(0xFF999999),
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.width(4.dp))
            }

            // Arrow
            if (hasArrow) {
                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = null,
                    tint = Color(0xFFcccccc),
                    modifier = Modifier.size(16.dp)
                )
            }
        }
    }
}

@Composable
fun RightContent() {
    var speakerEnabled by remember { mutableStateOf(true) }
    var volume by remember { mutableStateOf(0.5f) }
    var promptVolume by remember { mutableStateOf(1f) }
    var keySound by remember { mutableStateOf(true) }
    var microphoneEnabled by remember { mutableStateOf(false) }
    var brightness by remember { mutableStateOf(0.7f) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFf5f5f7))
            .padding(20.dp)
    ) {
        // Header with title and close button
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "声音与显示",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF222222),
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = { }) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = null,
                    tint = Color(0xFF666666),
                    modifier = Modifier.size(20.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Speaker section card
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = Color.White,
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                // Speaker toggle row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "扬声器",
                        color = Color(0xFF222222),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.weight(1f)
                    )
                    Switch(
                        checked = speakerEnabled,
                        onCheckedChange = { speakerEnabled = it },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = Color(0xFF217aff),
                            uncheckedThumbColor = Color.White,
                            uncheckedTrackColor = Color(0xFFdddddd)
                        )
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Volume
                Text(
                    text = "音量",
                    color = Color(0xFF666666),
                    fontSize = 13.sp,
                    modifier = Modifier.padding(bottom = 4.dp)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.VolumeDown,
                        contentDescription = null,
                        tint = Color(0xFF999999),
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Slider(
                        value = volume,
                        onValueChange = { volume = it },
                        modifier = Modifier.weight(1f),
                        colors = SliderDefaults.colors(
                            thumbColor = Color.White,
                            activeTrackColor = Color(0xFF217aff),
                            inactiveTrackColor = Color(0xFFe0e0e0)
                        )
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Prompt volume
                Text(
                    text = "提示音量",
                    color = Color(0xFF666666),
                    fontSize = 13.sp,
                    modifier = Modifier.padding(bottom = 4.dp)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.VolumeUp,
                        contentDescription = null,
                        tint = Color(0xFF999999),
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Slider(
                        value = promptVolume,
                        onValueChange = { promptVolume = it },
                        modifier = Modifier.weight(1f),
                        colors = SliderDefaults.colors(
                            thumbColor = Color.White,
                            activeTrackColor = Color(0xFF217aff),
                            inactiveTrackColor = Color(0xFFe0e0e0)
                        )
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Key sound toggle
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "按键音",
                        color = Color(0xFF222222),
                        fontSize = 14.sp,
                        modifier = Modifier.weight(1f)
                    )
                    Switch(
                        checked = keySound,
                        onCheckedChange = { keySound = it },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = Color(0xFF217aff),
                            uncheckedThumbColor = Color.White,
                            uncheckedTrackColor = Color(0xFFdddddd)
                        )
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Microphone toggle
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "麦克风",
                        color = Color(0xFF222222),
                        fontSize = 14.sp,
                        modifier = Modifier.weight(1f)
                    )
                    Switch(
                        checked = microphoneEnabled,
                        onCheckedChange = { microphoneEnabled = it },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = Color(0xFF217aff),
                            uncheckedThumbColor = Color.White,
                            uncheckedTrackColor = Color(0xFFdddddd)
                        )
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Brightness section card
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = Color.White,
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(
                    text = "亮度",
                    color = Color(0xFF666666),
                    fontSize = 13.sp,
                    modifier = Modifier.padding(bottom = 4.dp)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.LightMode,
                        contentDescription = null,
                        tint = Color(0xFF999999),
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Slider(
                        value = brightness,
                        onValueChange = { brightness = it },
                        modifier = Modifier.weight(1f),
                        colors = SliderDefaults.colors(
                            thumbColor = Color.White,
                            activeTrackColor = Color(0xFF217aff),
                            inactiveTrackColor = Color(0xFFe0e0e0)
                        )
                    )
                }
            }
        }
    }
}

@Composable
fun BottomBar() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 24.dp, end = 24.dp),
        horizontalArrangement = Arrangement.End,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // 新手指引
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Default.HelpOutline,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "新手指引",
                color = Color.White,
                fontSize = 13.sp
            )
        }

        Spacer(modifier = Modifier.width(24.dp))

        // 设置
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box {
                Icon(
                    imageVector = Icons.Default.Settings,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(20.dp)
                )
                // Notification dot
                Box(
                    modifier = Modifier
                        .size(5.dp)
                        .background(Color.Red, shape = RoundedCornerShape(2.5.dp))
                        .align(Alignment.TopEnd)
                )
            }
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "设置",
                color = Color.White,
                fontSize = 13.sp
            )
        }

        Spacer(modifier = Modifier.width(24.dp))

        // 电源
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Default.PowerSettingsNew,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "电源",
                color = Color.White,
                fontSize = 13.sp
            )
        }
    }
}
