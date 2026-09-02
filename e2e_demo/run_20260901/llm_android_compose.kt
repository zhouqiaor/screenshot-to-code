import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BrightnessHigh
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.VolumeDown
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SoundDisplaySettings() {
    val PrimaryColor = Color(0xFF1677FF)
    val BackgroundColor = Color(0xFFF5F5F5)
    val TextColor = Color(0xFF212121)

    var speakerEnabled by remember { mutableStateOf(true) }
    var volume by remember { mutableStateOf(0.7f) }
    var tipVolume by remember { mutableStateOf(0.5f) }
    var keySoundEnabled by remember { mutableStateOf(true) }
    var micEnabled by remember { mutableStateOf(false) }
    var brightness by remember { mutableStateOf(0.8f) }
    var selectedMenu by remember { mutableStateOf("声音与显示") }

    val menuItems = listOf(
        "企业服务配置" to null,
        "声音与显示" to null,
        "摄像机" to null,
        "壁纸" to "已设置",
        "Wi-Fi" to "已连接",
        "智慧功能" to null,
        "高级设置" to null
    )

    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = PrimaryColor,
            background = BackgroundColor,
            onBackground = TextColor,
            surface = Color.White
        )
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = BackgroundColor
        ) {
            Box(modifier = Modifier.fillMaxSize()) {
                // 窗口关闭按钮
                IconButton(
                    onClick = { /* 关闭窗口 */ },
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(16.dp)
                        .size(40.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "关闭",
                        tint = TextColor
                    )
                }

                // 主体水平布局
                Row(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(top = 64.dp, start = 16.dp, end = 16.dp, bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // 侧边栏
                    Surface(
                        modifier = Modifier
                            .width(240.dp)
                            .fillMaxHeight(),
                        shape = RoundedCornerShape(12.dp),
                        color = Color.White
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            // 侧边栏标题
                            Text(
                                text = "设置",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                color = TextColor
                            )

                            // 搜索输入框
                            OutlinedTextField(
                                value = "",
                                onValueChange = {},
                                placeholder = { Text("搜索设置项", fontSize = 14.sp) },
                                leadingIcon = {
                                    Icon(
                                        imageVector = Icons.Default.Search,
                                        contentDescription = "搜索",
                                        modifier = Modifier.size(20.dp)
                                    )
                                },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth(),
                                colors = androidx.compose.material3.OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = PrimaryColor,
                                    unfocusedBorderColor = Color(0xFFE0E0E0)
                                )
                            )

                            // 导航列表
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                menuItems.forEach { (item, status) ->
                                    val isSelected = item == selectedMenu
                                    Surface(
                                        onClick = { selectedMenu = item },
                                        shape = RoundedCornerShape(8.dp),
                                        color = if (isSelected) PrimaryColor.copy(alpha = 0.1f) else Color.Transparent
                                    ) {
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .padding(horizontal = 12.dp, vertical = 10.dp),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(
                                                text = item,
                                                color = if (isSelected) PrimaryColor else TextColor,
                                                fontWeight = if (isSelected) FontWeight.Medium else FontWeight.Normal,
                                                fontSize = 15.sp
                                            )
                                            status?.let {
                                                Text(
                                                    text = it,
                                                    fontSize = 12.sp,
                                                    color = if (isSelected) PrimaryColor else Color(0xFF999999)
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // 主内容区
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight(),
                        verticalArrangement = Arrangement.spacedBy(20.dp)
                    ) {
                        // 页面标题
                        Text(
                            text = "声音与显示",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = TextColor
                        )

                        // 声音设置卡片
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            color = Color.White
                        ) {
                            Column(
                                modifier = Modifier.padding(16.dp),
                                verticalArrangement = Arrangement.spacedBy(16.dp)
                            ) {
                                // 扬声器开关
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("扬声器", color = TextColor, fontSize = 16.sp)
                                    Switch(
                                        checked = speakerEnabled,
                                        onCheckedChange = { speakerEnabled = it },
                                        colors = SwitchDefaults.colors(
                                            checkedThumbColor = PrimaryColor,
                                            checkedTrackColor = PrimaryColor.copy(alpha = 0.5f)
                                        )
                                    )
                                }

                                // 音量滑块
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.VolumeUp,
                                        contentDescription = "音量",
                                        tint = TextColor,
                                        modifier = Modifier.size(24.dp)
                                    )
                                    Slider(
                                        value = volume,
                                        onValueChange = { volume = it },
                                        modifier = Modifier.weight(1f),
                                        colors = SliderDefaults.colors(
                                            thumbColor = PrimaryColor,
                                            activeTrackColor = PrimaryColor
                                        )
                                    )
                                }

                                // 提示音量滑块
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.VolumeDown,
                                        contentDescription = "提示音量",
                                        tint = TextColor,
                                        modifier = Modifier.size(24.dp)
                                    )
                                    Slider(
                                        value = tipVolume,
                                        onValueChange = { tipVolume = it },
                                        modifier = Modifier.weight(1f),
                                        colors = SliderDefaults.colors(
                                            thumbColor = PrimaryColor,
                                            activeTrackColor = PrimaryColor
                                        )
                                    )
                                }

                                // 按键音开关
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("按键音", color = TextColor, fontSize = 16.sp)
                                    Switch(
                                        checked = keySoundEnabled,
                                        onCheckedChange = { keySoundEnabled = it },
                                        colors = SwitchDefaults.colors(
                                            checkedThumbColor = PrimaryColor,
                                            checkedTrackColor = PrimaryColor.copy(alpha = 0.5f)
                                        )
                                    )
                                }

                                // 麦克风开关
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("麦克风", color = TextColor, fontSize = 16.sp)
                                    Switch(
                                        checked = micEnabled,
                                        onCheckedChange = { micEnabled = it },
                                        colors = SwitchDefaults.colors(
                                            checkedThumbColor = PrimaryColor,
                                            checkedTrackColor = PrimaryColor.copy(alpha = 0.5f)
                                        )
                                    )
                                }
                            }
                        }

                        // 亮度设置卡片
                        Surface(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            color = Color.White
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.BrightnessHigh,
                                    contentDescription = "亮度",
                                    tint = TextColor,
                                    modifier = Modifier.size(24.dp)
                                )
                                Slider(
                                    value = brightness,
                                    onValueChange = { brightness = it },
                                    modifier = Modifier.weight(1f),
                                    colors = SliderDefaults.colors(
                                        thumbColor = PrimaryColor,
                                        activeTrackColor = PrimaryColor
                                    )
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}