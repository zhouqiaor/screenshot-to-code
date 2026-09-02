using Microsoft.UI.Xaml;

namespace E2EApp
{
    public partial class App : Application
    {
        private Window? _window;

        public App()
        {
            this.InitializeComponent();
        }

        protected override void OnLaunched(LaunchActivatedEventArgs args)
        {
            _window = new Window();
            _window.Content = new SettingsPage();
            _window.Activate();
        }
    }
}
