package com.example.settings

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun SettingsScreen() {
    var notifEnabled by remember { mutableStateOf(true) }
    var darkEnabled by remember { mutableStateOf(false) }
    var selectedLang by remember { mutableStateOf("English") }
    val languages = listOf("English", "简体中文")
    var dropdownExpanded by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("Settings", style = MaterialTheme.typography.headlineMedium)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Enable notifications")
            Switch(checked = notifEnabled, onCheckedChange = { notifEnabled = it })
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Dark theme")
            Switch(checked = darkEnabled, onCheckedChange = { darkEnabled = it })
        }
        Text("Language")
        ExposedDropdownMenuBox(expanded = dropdownExpanded, onExpandedChange = { dropdownExpanded = it }) {
            TextField(
                value = selectedLang,
                onValueChange = {},
                readOnly = true,
                modifier = Modifier.menuAnchor().fillMaxWidth()
            )
            ExposedDropdownMenu(expanded = dropdownExpanded, onDismissRequest = { dropdownExpanded = false }) {
                languages.forEach { lang ->
                    DropdownMenuItem(text = { Text(lang) }, onClick = {
                        selectedLang = lang
                        dropdownExpanded = false
                    })
                }
            }
        }
        Button(
            onClick = { /* Persist settings */ },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF007AFF))
        ) { Text("Save", color = Color.White) }
    }
}