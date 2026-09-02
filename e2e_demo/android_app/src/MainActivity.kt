package com.example.settings

import android.app.Activity
import android.os.Bundle
import android.view.View
import android.widget.*
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Switch
import android.widget.Spinner
import android.widget.Button

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        val spinner = findViewById<Spinner>(R.id.spinner_language)
        val btn = findViewById<Button>(R.id.btn_save)
        val switchNotif = findViewById<Switch>(R.id.switch_notif)
        
        btn.setOnClickListener {
            Toast.makeText(this, "Settings saved: notif=${switchNotif.isChecked}", Toast.LENGTH_SHORT).show()
        }
    }
}
