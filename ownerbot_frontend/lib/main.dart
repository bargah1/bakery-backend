import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:google_fonts/google_fonts.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:intl/intl.dart'; // For date formatting
import 'package:image_picker/image_picker.dart'; // For image picking
import 'dart:io' show File; // For File operations (mobile)
import 'dart:typed_data'; // For BytesSource in audioplayers
import 'package:flutter/foundation.dart' show kIsWeb; // To check if running on web
import 'package:http_parser/http_parser.dart'; // For MediaType in MultipartFile
import 'package:fl_chart/fl_chart.dart'; // For charts
import 'package:audioplayers/audioplayers.dart'; // For playing audio
import 'package:flutter/services.dart'; // Needed for Clipboard
import 'package:url_launcher/url_launcher.dart'; // For launching URLs/phone numbers
import 'package:flutter_local_notifications/flutter_local_notifications.dart'; // For notifications

// --- Main App Setup ---
// IMPORTANT: For physical devices, replace with your computer's local network IP address.
// For example: 'http://192.168.1.7:8000' or 'http://your_server_ip:8000'
const String API_BASE_URL = 'https://bakery-backend-5qkn.onrender.com';


// Notification Service for low stock alerts
class NotificationService {
  static final FlutterLocalNotificationsPlugin _notificationsPlugin = FlutterLocalNotificationsPlugin();

  static void initialize() {
    const InitializationSettings initializationSettings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      iOS: DarwinInitializationSettings(),
    );
    _notificationsPlugin.initialize(initializationSettings);
  }

  static void showNotification(String title, String body) async {
    const NotificationDetails notificationDetails = NotificationDetails(
      android: AndroidNotificationDetails(
        'low_stock_channel',
        'Low Stock Alerts',
        channelDescription: 'Notifications for when stock is running low',
        importance: Importance.max,
        priority: Priority.high,
        ticker: 'ticker',
        styleInformation: BigTextStyleInformation(''),
      ),
    );
    await _notificationsPlugin.show(0, title, body, notificationDetails);
  }
}

void main() => runApp(const OwnerBotApp());

// Helper function to convert text to Title Case
String _toTitleCase(String text) {
  if (text.isEmpty) return '';
  return text.split(' ').map((str) => str.isNotEmpty ? '${str[0].toUpperCase()}${str.substring(1).toLowerCase()}' : '').join(' ');
}

// Main entry point of the Flutter application

// The root widget of the OwnerBot application
class OwnerBotApp extends StatelessWidget {
  const OwnerBotApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OwnerBot',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6A0B0B),
          primary: const Color(0xFF6A0B0B),
          secondary: Colors.amber.shade700,
          background: const Color(0xFFF8F7F5),
          surface: Colors.white,
          error: Colors.red.shade800,
        ),
        scaffoldBackgroundColor: const Color(0xFFFFF8F1),
        textTheme: GoogleFonts.interTextTheme(Theme.of(context).textTheme),
        appBarTheme: AppBarTheme(
          backgroundColor: const Color(0xFF6A0B0B),
          foregroundColor: Colors.white,
          elevation: 4,
          shadowColor: Colors.black.withOpacity(0.2),
          centerTitle: true,
          titleTextStyle: GoogleFonts.inter(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12.0)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12.0), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12.0), borderSide: const BorderSide(color: Color(0xFF6A0B0B), width: 2.0)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
        ),
        cardTheme: CardTheme(elevation: 2, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)), margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8)),
      ),
      home: const OwnerBotHomePage(), // Use the comprehensive homepage
      debugShowCheckedModeBanner: false,
    );
  }
}
// --- Home Page and Navigation ---
// This widget manages the main navigation drawer and displays the selected screen.
class OwnerBotHomePage extends StatefulWidget {
  const OwnerBotHomePage({super.key});
  @override
  State<OwnerBotHomePage> createState() => _OwnerBotHomePageState();
}

class _OwnerBotHomePageState extends State<OwnerBotHomePage> {
  int _selectedIndex = 0; // Current selected index for navigation

  @override
  void initState() {
    super.initState();
    NotificationService.initialize(); // Initialize notification service
    _checkForLowStock(); // Check for low stock alerts on app start
  }
  
  // Fetches low stock alerts from the backend and shows a notification
  Future<void> _checkForLowStock() async {
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/reports/low-stock-alerts/'));
      if(response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final List products = data['low_stock_products'];
        final List ingredients = data['low_stock_ingredients'];

        if (products.isNotEmpty || ingredients.isNotEmpty) {
          String body = '';
          if (products.isNotEmpty) body += 'Products: ${products.map((p) => p['name']).join(', ')}. ';
          if (ingredients.isNotEmpty) body += 'Ingredients: ${ingredients.map((i) => i['name']).join(', ')}.';
          NotificationService.showNotification('Low Stock Alert!', body);
        }
      }
    } catch(e) {
      print("Failed to check for low stock alerts: $e");
    }
  }

  // List of widgets (screens) corresponding to navigation items
  static final List<Widget> _widgetOptions = <Widget>[
    const DashboardScreen(),
    const ProfitLossScreen(),
    const OwnerBotChat(),
    const SalesReporterScreen(),
    const ProductionReporterScreen(),
    const InventoryReporterScreen(),
    const StaffManagementScreen(),
    const StaffAttendanceReportScreen(),
    const ExpenseManagementScreen(),
    const CCTVReportScreen(),
    const CustomerReportScreen(),
    const ProductManagementScreen(),
    const OutletManagementScreen(), 
    const AboutScreen(), 
  ];

  // Titles for the navigation drawer items
  final List<String> _titles = [
    'Dashboard', 'Profit & Loss', 'Chat with Bot', 'Sales Report', 
    'Production Report', 'Inventory Report', 'Staff Management', 
    'Staff Attendance Report', 'Expense Tracker', 'CCTV Observations', 
    'Customer Report', 'Manage Products', 'Manage Outlets', 'About'
  ];
  // Icons for the navigation drawer items
  final List<IconData> _icons = [
    Icons.dashboard, Icons.trending_up, Icons.chat, Icons.show_chart, 
    Icons.factory, Icons.inventory, Icons.people, Icons.calendar_month, 
    Icons.money_off, Icons.videocam, Icons.shopping_cart, Icons.settings, 
    Icons.store, Icons.info_outline
  ];

  // Callback for when a navigation item is tapped
  void _onItemTapped(int index) {
    setState(() => _selectedIndex = index); // Update selected index
    Navigator.pop(context); // Close the drawer
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // AppBar for the main Scaffold, dynamically changes title
      appBar: AppBar(
        title: Text(
          _titles[_selectedIndex], // Display the title of the currently selected screen
          style: Theme.of(context).appBarTheme.titleTextStyle, // Use app bar theme text style
        ),
      ),
      // Navigation Drawer
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: <Widget>[
            // Drawer header with app title
            DrawerHeader(
              decoration: BoxDecoration(color: Theme.of(context).colorScheme.primary),
              child: Text('Manager Dashboard', style: GoogleFonts.inter(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
            ),
            // List of navigation items
            for (var i = 0; i < _titles.length; i++)
              ListTile(
                leading: Icon(_icons[i]), // Item icon
                title: Text(_titles[i]), // Item title
                selected: _selectedIndex == i, // Highlight if selected
                onTap: () => _onItemTapped(i), // Handle tap
              ),
          ],
        ),
      ),
      // Display the currently selected screen in the body
      body: _widgetOptions.elementAt(_selectedIndex),
    );
  }
}

// ===================================================================
// Dashboard Screen - Displays key performance indicators
// ===================================================================
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic> _dashboardData = {};
  List<dynamic> _lowStockItems = [];
  bool _isLoading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _fetchDashboardData();
  }

  Future<void> _fetchDashboardData() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _error = '';
    });
    try {
      final summaryUri = Uri.parse('$API_BASE_URL/reports/dashboard-summary/');
      final lowStockUri = Uri.parse('$API_BASE_URL/reports/low-stock-alerts/');

      // Use Future.wait for more efficient parallel fetching
      final responses = await Future.wait([
        http.get(summaryUri),
        http.get(lowStockUri),
      ]);

      if (!mounted) return;

      if (responses[0].statusCode == 200) {
        _dashboardData = jsonDecode(utf8.decode(responses[0].bodyBytes));
      } else {
        throw Exception('Failed to load dashboard summary');
      }

      if (responses[1].statusCode == 200) {
        // First, decode the JSON object into a Map
        final Map<String, dynamic> data = jsonDecode(utf8.decode(responses[1].bodyBytes));
        
        // Safely get the lists from the Map
        final List products = data['low_stock_products'] ?? [];
        final List ingredients = data['low_stock_ingredients'] ?? [];

        // Combine both lists into the one list your UI uses
        _lowStockItems = [...products, ...ingredients];
        
      } else {
        throw Exception('Failed to load low stock items');
      }
    } catch (e) {
      if (mounted) {
        _error = 'Error loading dashboard: $e';
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error.isNotEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error, style: const TextStyle(color: Colors.red), textAlign: TextAlign.center),
              const SizedBox(height: 16),
              IconButton(
                icon: const Icon(Icons.refresh, size: 32),
                onPressed: _fetchDashboardData,
              )
            ],
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _fetchDashboardData,
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildSummaryCards(),
          const SizedBox(height: 24),
          _buildLowStockSection(),
        ],
      ),
    );
  }

  Widget _buildSummaryCards() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      childAspectRatio: 1.2,
      children: [
        _buildInfoCard(
          context,
          icon: Icons.point_of_sale,
          title: 'Today\'s Sales',
          value: '₹${_dashboardData['today_sales']?.toStringAsFixed(2) ?? '0.00'}',
          color: Colors.green,
        ),
        _buildInfoCard(
          context,
          icon: Icons.trending_up,
          title: 'This Month',
          value: '₹${_dashboardData['this_month_sales']?.toStringAsFixed(2) ?? '0.00'}',
          color: Colors.blue,
        ),
        _buildInfoCard(
          context,
          icon: Icons.shopping_cart,
          title: 'Total Orders',
          value: _dashboardData['total_orders_today']?.toString() ?? '0',
          color: Colors.orange,
        ),
        _buildInfoCard(
          context,
          icon: Icons.bakery_dining,
          title: 'Items Sold',
          value: _dashboardData['total_items_sold_today']?.toString() ?? '0',
          color: Colors.purple,
        ),
      ],
    );
  }

  Widget _buildInfoCard(BuildContext context, {required IconData icon, required String title, required String value, required Color color}) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            CircleAvatar(
              backgroundColor: color.withOpacity(0.1),
              child: Icon(icon, color: color),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                Text(title, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey.shade600)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLowStockSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Low Stock Items',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        _lowStockItems.isEmpty
            ? const Card(
                child: Padding(
                  padding: EdgeInsets.all(24.0),
                  child: Center(child: Text('All items are well-stocked!')),
                ),
              )
            : ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _lowStockItems.length,
                itemBuilder: (context, index) {
                  final item = _lowStockItems[index];
                  return Card(
                    color: Colors.orange.shade50,
                    child: ListTile(
                      leading: const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                      title: Text(item['name'] ?? 'Unknown Item', style: const TextStyle(fontWeight: FontWeight.bold)),
                      trailing: Text(
                        'Stock: ${item['stock']}',
                        style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.red, fontSize: 16),
                      ),
                    ),
                  );
                },
              ),
      ],
    );
  }
}


// ===================================================================
// Profit & Loss Screen - Displays financial report for a date range
// ===================================================================
class ProfitLossScreen extends StatefulWidget {
  const ProfitLossScreen({super.key});
  @override
  _ProfitLossScreenState createState() => _ProfitLossScreenState();
}

class _ProfitLossScreenState extends State<ProfitLossScreen> {
  Map<String, dynamic>? _reportData;
  bool _isLoading = true;
  String _error = '';
  DateTime? _startDate, _endDate;

  @override
  void initState() {
    super.initState();
    _startDate = DateTime(DateTime.now().year, DateTime.now().month, 1);
    _endDate = DateTime.now();
    _fetchReport();
  }

  Future<void> _fetchReport() async {
    setState(() { _isLoading = true; _error = ''; });
    try {
      final uri = Uri.parse('$API_BASE_URL/reports/profit-loss/').replace(queryParameters: {
        'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
        'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
      });
      final response = await http.get(uri);
      if (mounted) {
        if (response.statusCode == 200) {
          setState(() {
            _reportData = jsonDecode(utf8.decode(response.bodyBytes));
            _isLoading = false;
          });
        } else {
          throw Exception('Failed to load report: ${response.statusCode}');
        }
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Failed to load report: $e'; _isLoading = false; });
    }
  }

  Future<void> _selectDateRange(BuildContext context) async {
    final picked = await showDateRangePicker(
      context: context,
      initialDateRange: DateTimeRange(start: _startDate!, end: _endDate!),
      firstDate: DateTime(2023),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() { _startDate = picked.start; _endDate = picked.end; });
      _fetchReport();
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
    ));
  }

  void _copyReport() {
    if (_reportData == null) return;
    String report = "Profit & Loss Report (${DateFormat.yMMMd().format(_startDate!)} to ${DateFormat.yMMMd().format(_endDate!)})\n\n";
    report += "Total Revenue: ₹${_reportData!['total_revenue']}\n\n";
    report += "--- COSTS ---\n";
    report += "Cost of Goods Sold: ₹${_reportData!['cost_of_goods_sold']}\n";
    report += "Salary Expenses: ₹${_reportData!['salary_expenses']}\n";
    report += "Operating Expenses: ₹${_reportData!['operating_expenses']}\n";
    report += "Total Expenses: ₹${_reportData!['total_expenses']}\n";
    report += "--------------------\n";
    report += "Net Profit: ₹${_reportData!['net_profit']}\n";
    
    Clipboard.setData(ClipboardData(text: report));
    _showSnackBar("Report copied to clipboard!");
  }

  Future<void> _clearData() async {
    final confirm = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
            title: const Text('Confirm Clear Data'),
            content: Text('Are you sure you want to delete ALL sales and expenses from ${DateFormat.yMMMd().format(_startDate!)} to ${DateFormat.yMMMd().format(_endDate!)}? This action cannot be undone.'),
            actions: [
                TextButton(child: const Text('Cancel'), onPressed: () => Navigator.of(ctx).pop(false)),
                TextButton(child: const Text('DELETE', style: TextStyle(color: Colors.red)), onPressed: () => Navigator.of(ctx).pop(true)),
            ],
        ),
    );

    if (confirm != true) return;

    setState(() => _isLoading = true);
    try {
        final uri = Uri.parse('$API_BASE_URL/reports/clear-data/').replace(queryParameters: {
            'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
            'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
        });
        final response = await http.delete(uri);

        if (mounted) {
            if (response.statusCode == 200) {
                final data = jsonDecode(response.body);
                _showSnackBar(data['message'] ?? "Data cleared successfully");
                _fetchReport();
            } else {
                throw Exception('Failed to clear data: ${response.body}');
            }
        }
    } catch(e) {
        if(mounted) {
            _showSnackBar('Error: $e', isError: true);
        }
    } finally {
        if(mounted) setState(() => _isLoading = false);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final double revenue = (_reportData?['total_revenue'] as num?)?.toDouble() ?? 0.0;
    final double expenses = (_reportData?['total_expenses'] as num?)?.toDouble() ?? 0.0;
    final double profit = (_reportData?['net_profit'] as num?)?.toDouble() ?? 0.0;
    final Map<String, dynamic> expenseBreakdown = _reportData?['expense_breakdown'] ?? {};

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _fetchReport,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              ElevatedButton.icon(
                onPressed: () => _selectDateRange(context),
                icon: const Icon(Icons.calendar_today),
                label: Text('${DateFormat.yMMMd().format(_startDate!)} - ${DateFormat.yMMMd().format(_endDate!)}'),
                style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
              ),
              const SizedBox(height: 16),
              if (_isLoading)
                const Expanded(child: Center(child: CircularProgressIndicator()))
              else if (_error.isNotEmpty)
                Expanded(child: Center(child: Text(_error)))
              else
                Expanded(
                  child: ListView(
                    children: [
                      Row(
                        children: [
                          _buildKpiCard('Total Revenue', '₹${revenue.toStringAsFixed(2)}', Colors.green, Icons.arrow_upward),
                          const SizedBox(width: 16),
                          _buildKpiCard('Total Expenses', '₹${expenses.toStringAsFixed(2)}', Colors.red, Icons.arrow_downward),
                        ],
                      ),
                      const SizedBox(height: 16),
                      _buildKpiCard('Net Profit', '₹${profit.toStringAsFixed(2)}', profit >= 0 ? Colors.blue : Colors.deepOrange, Icons.calculate, isLarge: true),
                      const SizedBox(height: 24),
                      Text("Expense Breakdown", style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                      const Divider(),
                      SizedBox(
                        height: 250,
                        child: expenseBreakdown.isEmpty
                          ? const Center(child: Text('No expense data for this period.'))
                          : PieChart(_buildPieChartData(expenseBreakdown)),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          FloatingActionButton(onPressed: _isLoading ? null : _fetchReport, tooltip: 'Refresh', heroTag: 'refresh_profit', child: const Icon(Icons.refresh)),
          const SizedBox(height: 10),
          FloatingActionButton(onPressed: _isLoading || _reportData == null ? null : _copyReport, tooltip: 'Copy Report', heroTag: 'copy_profit', backgroundColor: Colors.blue, child: const Icon(Icons.copy)),
          const SizedBox(height: 10),
          FloatingActionButton(onPressed: _isLoading ? null : _clearData, tooltip: 'Clear Data in Range', heroTag: 'clear_profit', backgroundColor: Theme.of(context).colorScheme.error, child: const Icon(Icons.delete_forever)),
        ],
      ),
    );
  }

  Widget _buildKpiCard(String title, String value, Color color, IconData icon, {bool isLarge = false}) {
    return Expanded(
      child: Card(
        color: color.withOpacity(0.1),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15), side: BorderSide(color: color.withOpacity(0.3))),
        child: Padding(
          padding: EdgeInsets.all(isLarge ? 24 : 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(title, style: TextStyle(color: color, fontWeight: FontWeight.bold)),
                  Icon(icon, color: color),
                ],
              ),
              const SizedBox(height: 8),
              Text(value, style: TextStyle(fontSize: isLarge ? 32 : 24, fontWeight: FontWeight.bold, color: color)),
            ],
          ),
        ),
      ),
    );
  }

  PieChartData _buildPieChartData(Map<String, dynamic> breakdown) {
    final List<Color> pieColors = [Colors.red, Colors.orange, Colors.amber, Colors.lightBlue, Colors.purple, Colors.brown];
    int colorIndex = 0;
    
    return PieChartData(
      sections: breakdown.entries.map((entry) {
        final color = pieColors[colorIndex++ % pieColors.length];
        return PieChartSectionData(
          color: color,
          value: (entry.value as num).toDouble(),
          title: '${_toTitleCase(entry.key)}\n₹${(entry.value as num).toStringAsFixed(0)}',
          radius: 100,
          titleStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white, shadows: [Shadow(color: Colors.black, blurRadius: 2)]),
        );
      }).toList(),
      sectionsSpace: 2,
      centerSpaceRadius: 0,
    );
  }
}


// ===================================================================
// Expense Management Screen - Allows adding, editing, and deleting expenses
// ===================================================================
class ExpenseManagementScreen extends StatefulWidget {
  const ExpenseManagementScreen({super.key});
  @override
  _ExpenseManagementScreenState createState() => _ExpenseManagementScreenState();
}

class _ExpenseManagementScreenState extends State<ExpenseManagementScreen> {
  List<dynamic> _expenses = []; // List of expenses
  bool _isLoading = true; // Loading state
  String _error = ''; // Error message
  DateTime? _startDate, _endDate; // Date range for expenses

  @override
  void initState() {
    super.initState();
    // Default date range: first day of current month to today
    _startDate = DateTime(DateTime.now().year, DateTime.now().month, 1);
    _endDate = DateTime.now();
    _fetchExpenses(); // Fetch expenses on init
  }

  // Fetches expenses from the backend for the selected date range
  Future<void> _fetchExpenses() async {
    setState(() { _isLoading = true; _error = ''; }); // Set loading state
    try {
      // Construct URI with date parameters
      final uri = Uri.parse('$API_BASE_URL/expenses/manage/').replace(queryParameters: {
        'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
        'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
      });
      final response = await http.get(uri);
      if (mounted) {
        if (response.statusCode == 200) {
          setState(() {
            _expenses = jsonDecode(utf8.decode(response.bodyBytes)); // Parse data
            _isLoading = false; // End loading
          });
        } else {
          throw Exception('Failed to load expenses'); // Throw error
        }
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Failed to load expenses: $e'; _isLoading = false; }); // Set error state
    }
  }

  // Shows a date range picker to select expense dates
  Future<void> _selectDateRange(BuildContext context) async {
    final picked = await showDateRangePicker(
      context: context,
      initialDateRange: DateTimeRange(start: _startDate!, end: _endDate!),
      firstDate: DateTime(2023),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() { _startDate = picked.start; _endDate = picked.end; }); // Update dates
      _fetchExpenses(); // Fetch expenses with new dates
    }
  }
  
  // Shows the expense dialog for adding or editing an expense
  void _showExpenseDialog({Map<String, dynamic>? expense}) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _ExpenseDialog(expense: expense, onSave: _fetchExpenses), // Pass expense for editing, onSave to refresh list
    );
  }

  // Deletes an expense by its ID
  void _deleteExpense(String expenseId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(title: const Text('Confirm Deletion'), content: const Text('Are you sure? This cannot be undone.'), actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
        TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Delete', style: TextStyle(color: Colors.red))),
      ])
    );
    if (confirm != true) return; // If user cancels, do nothing

    try {
      final response = await http.delete(Uri.parse('$API_BASE_URL/expenses/manage/$expenseId/')); // Send DELETE request
      if (response.statusCode == 204) { // 204 No Content indicates successful deletion
        _showSnackBar('Expense deleted successfully!', isError: false);
        _fetchExpenses(); // Refresh the list
      } else { throw Exception('Failed to delete expense'); } // Throw error
    } catch(e) { _showSnackBar('Error: $e', isError: true); } // Show error message
  }

  // Copies the expense report text to clipboard
  void _copyExpenseReport() {
    String report = "Expense Report (${DateFormat.yMMMd().format(_startDate!)} - ${DateFormat.yMMMd().format(_endDate!)})\n\n";
    double total = 0;
    for(var exp in _expenses) {
        report += "${exp['date']} - ${exp['description']} (${exp['category']}): ₹${exp['amount']}\n";
        total += (exp['amount'] as num).toDouble();
    }
    report += "\n--------------------\n";
    report += "Total Expenses: ₹${total.toStringAsFixed(2)}";
    Clipboard.setData(ClipboardData(text: report)); // Copy to clipboard
    _showSnackBar("Report copied to clipboard!");
  }
  
  // Shows a SnackBar message
  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
    ));
  }

  @override
  Widget build(BuildContext context) {
    // Calculate total expenses from the loaded list
    double totalExpenses = _expenses.fold(0.0, (sum, item) => sum + (item['amount'] as num));
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Date range selection button
            ElevatedButton.icon(onPressed: () => _selectDateRange(context), icon: const Icon(Icons.calendar_today), label: Text('${DateFormat.yMMMd().format(_startDate!)} - ${DateFormat.yMMMd().format(_endDate!)}')),
            const SizedBox(height: 16),
            // Conditional display for loading/error/list
            if (_isLoading) Expanded(child: const Center(child: CircularProgressIndicator())) else Expanded(
              child: ListView.builder(
                itemCount: _expenses.length,
                itemBuilder: (context, index) {
                  final expense = _expenses[index];
                  return Card(
                    child: ListTile(
                      title: Text(expense['description'], style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text(expense['category']),
                      trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                          Text('₹${(expense['amount'] as num).toStringAsFixed(2)}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.red)),
                          IconButton(icon: Icon(Icons.delete_outline, color: Colors.red.shade300), onPressed: () => _deleteExpense(expense['id'])),
                      ]),
                      onTap: () => _showExpenseDialog(expense: expense), // Tap to edit
                    ),
                  );
                },
              ),
            ),
            // Total expenses display
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Total:', style: Theme.of(context).textTheme.titleLarge),
                Text('₹${totalExpenses.toStringAsFixed(2)}', style: Theme.of(context).textTheme.titleLarge?.copyWith(color: Colors.red, fontWeight: FontWeight.bold)),
              ],
            ),
            const SizedBox(height: 16),
            // Copy report button
            ElevatedButton.icon(onPressed: _copyExpenseReport, icon: const Icon(Icons.copy), label: const Text("Copy Report"))
          ],
        ),
      ),
      // Floating Action Button to add new expense
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showExpenseDialog(),
        tooltip: 'Add Expense',
        child: const Icon(Icons.add),
      ),
    );
  }
}

// --- Dialog for adding/editing expenses ---
class _ExpenseDialog extends StatefulWidget {
  final Map<String, dynamic>? expense; // Expense data for editing (null for new)
  final VoidCallback onSave; // Callback to refresh list after save
  const _ExpenseDialog({this.expense, required this.onSave});

  @override
  _ExpenseDialogState createState() => _ExpenseDialogState();
}

class _ExpenseDialogState extends State<_ExpenseDialog> {
  final _formKey = GlobalKey<FormState>(); // Form key for validation
  late TextEditingController _descController, _amountController; // Text controllers
  String _category = 'Utilities'; // Selected expense category
  DateTime _selectedDate = DateTime.now(); // Selected date
  bool _isSaving = false; // Saving state
  bool get _isEditing => widget.expense != null; // Check if in editing mode

  @override
  void initState() {
    super.initState();
    // Initialize controllers with existing data if editing
    _descController = TextEditingController(text: widget.expense?['description'] ?? '');
    _amountController = TextEditingController(text: widget.expense?['amount']?.toString() ?? '');
    _category = widget.expense?['category'] ?? 'Utilities';
    _selectedDate = widget.expense != null ? DateTime.parse(widget.expense!['date']) : DateTime.now();
  }

  // Saves (adds or updates) the expense to the backend
  Future<void> _saveExpense() async {
    if (!_formKey.currentState!.validate()) return; // Validate form
    setState(() => _isSaving = true); // Set saving state

    // Prepare data payload
    final data = {
      'description': _descController.text,
      'amount': double.parse(_amountController.text),
      'category': _category,
      'date': DateFormat('yyyy-MM-dd').format(_selectedDate),
    };
    
    // Determine URL and HTTP method based on editing or adding
    final url = _isEditing ? '$API_BASE_URL/expenses/manage/${widget.expense!['id']}/' : '$API_BASE_URL/expenses/manage/';
    
    try {
      http.Response response;
      if (_isEditing) {
        response = await http.put( // Use PUT for updating
          Uri.parse(url),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(data),
        );
      } else {
        response = await http.post( // Use POST for adding
          Uri.parse(url),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(data),
        );
      }

      if (mounted) {
        if (response.statusCode == 200 || response.statusCode == 201) {
          widget.onSave(); // Call onSave callback to refresh parent list
          Navigator.of(context).pop(); // Close the dialog
        } else {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error saving expense: ${response.body}')));
        }
      }
    } catch(e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Network error: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false); // End saving state
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEditing ? 'Edit Expense' : 'Add Expense'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Description input field
              TextFormField(controller: _descController, decoration: const InputDecoration(labelText: 'Description'), validator: (v) => v!.isEmpty ? 'Required' : null),
              // Amount input field
              TextFormField(controller: _amountController, decoration: const InputDecoration(labelText: 'Amount', prefixText: '₹'), keyboardType: TextInputType.number, validator: (v) => v!.isEmpty ? 'Required' : null),
              // Category dropdown
              DropdownButtonFormField<String>(
                value: _category,
                decoration: const InputDecoration(labelText: 'Category'),
                items: ['Utilities', 'Rent', 'Salaries', 'Raw Materials', 'Marketing', 'Other'].map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                onChanged: (val) => setState(() => _category = val!),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(onPressed: _isSaving ? null : _saveExpense, child: _isSaving ? const CircularProgressIndicator() : const Text('Save')),
      ],
    );
  }
}

// ===================================================================
// OutletManagementScreen - Manages bakery outlets/production units
// ===================================================================
class OutletManagementScreen extends StatefulWidget {
  const OutletManagementScreen({super.key});
  @override
  _OutletManagementScreenState createState() => _OutletManagementScreenState();
}

class _OutletManagementScreenState extends State<OutletManagementScreen> {
  late Future<List<dynamic>> _outletsFuture; // Future to hold fetched outlets

  @override
  void initState() {
    super.initState();
    _outletsFuture = _fetchOutlets(); // Fetch outlets on init
  }

  // Fetches all outlets from the backend
  Future<List<dynamic>> _fetchOutlets() async {
    final response = await http.get(Uri.parse('$API_BASE_URL/outlets/manage/'));
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)); // Parse and return data
    } else {
      throw Exception('Failed to load outlets'); // Throw error
    }
  }

  // Refreshes the list of outlets
  void _refreshOutlets() {
    setState(() { _outletsFuture = _fetchOutlets(); }); // Re-fetch outlets
  }

  // Deletes an outlet by its ID
  void _deleteOutlet(String outletId, String outletName) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete outlet "$outletName"?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              Navigator.of(ctx).pop(); // Close dialog
              try {
                final response = await http.delete(Uri.parse('$API_BASE_URL/outlets/manage/$outletId/')); // Send DELETE request
                if (response.statusCode == 204) { // 204 No Content indicates successful deletion
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Outlet deleted'), backgroundColor: Colors.green));
                  _refreshOutlets(); // Refresh the list
                } else {
                  throw Exception('Failed to delete outlet'); // Throw error
                }
              } catch(e) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error deleting outlet: $e'), backgroundColor: Colors.red));
              }
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  // Shows the outlet dialog for adding or editing an outlet
  void _showOutletDialog({Map<String, dynamic>? outlet}) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _OutletDialog(outlet: outlet, onSave: _refreshOutlets), // Pass outlet for editing, onSave to refresh list
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator( // Pull to refresh functionality
        onRefresh: _fetchOutlets,
        child: FutureBuilder<List<dynamic>>( // Use FutureBuilder to handle async data
          future: _outletsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator()); // Show loading
            }
            if (snapshot.hasError || !snapshot.hasData || snapshot.data!.isEmpty) {
              return const Center(child: Text('No outlets found. Add one!')); // Show error/empty message
            }
            final outlets = snapshot.data!; // Get the list of outlets
            return ListView.builder( // Display outlets in a list
              itemCount: outlets.length,
              itemBuilder: (context, index) {
                final outlet = outlets[index];
                // Determine icon and color based on outlet type
                final isProduction = outlet['type'] == 'production';
                final icon = isProduction ? Icons.factory : Icons.store;
                final color = isProduction ? Colors.blue.shade700 : Colors.green.shade700;

                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: ListTile(
                    leading: CircleAvatar(backgroundColor: color, child: Icon(icon, color: Colors.white)),
                    title: Text(outlet['name'] ?? 'No Name', style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text('Phone: ${outlet['phone'] ?? 'N/A'}'),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Chip to display outlet type
                        Chip(
                          label: Text(_toTitleCase(outlet['type'] ?? 'sales')),
                          backgroundColor: color.withOpacity(0.1),
                          labelStyle: TextStyle(color: color),
                        ),
                        // Delete button
                        IconButton(
                          icon: const Icon(Icons.delete, color: Colors.red),
                          onPressed: () => _deleteOutlet(outlet['id'], outlet['name']),
                        ),
                      ],
                    ),
                    onTap: () => _showOutletDialog(outlet: outlet), // Tap to edit
                  ),
                );
              },
            );
          },
        ),
      ),
      floatingActionButton: FloatingActionButton( // Button to add new outlet
        onPressed: () => _showOutletDialog(),
        tooltip: 'Add Outlet',
        child: const Icon(Icons.add),
      ),
    );
  }
}

// --- DIALOG FOR ADDING/EDITING OUTLETS ---
class _OutletDialog extends StatefulWidget {
  final Map<String, dynamic>? outlet; // Outlet data for editing (null for new)
  final VoidCallback onSave; // Callback to refresh list after save
  const _OutletDialog({this.outlet, required this.onSave});
  @override
  _OutletDialogState createState() => _OutletDialogState();
}

class _OutletDialogState extends State<_OutletDialog> {
  final _formKey = GlobalKey<FormState>(); // Form key for validation
  late TextEditingController _nameController, _phoneController; // Text controllers
  String _outletType = 'sales'; // Default outlet type
  bool _isSaving = false; // Saving state
  bool get _isEditing => widget.outlet != null; // Check if in editing mode

  @override
  void initState() {
    super.initState();
    // Initialize controllers with existing data if editing
    _nameController = TextEditingController(text: widget.outlet?['name'] ?? '');
    _phoneController = TextEditingController(text: widget.outlet?['phone'] ?? '');
    _outletType = widget.outlet?['type'] ?? 'sales';
  }
  
  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  // Saves (adds or updates) the outlet to the backend
  Future<void> _saveOutlet() async {
    if (!_formKey.currentState!.validate() || _isSaving) return; // Validate form and check saving state
    setState(() => _isSaving = true); // Set saving state
    
    // Prepare data payload
    final outletData = {
      'name': _nameController.text,
      'phone': _phoneController.text,
      'type': _outletType, // Include the type in the data
    };

    // Determine URL and HTTP method based on editing or adding
    final url = _isEditing 
      ? '$API_BASE_URL/outlets/manage/${widget.outlet!['id']}/'
      : '$API_BASE_URL/outlets/manage/';
    
    final request = http.Request(_isEditing ? 'PUT' : 'POST', Uri.parse(url))
      ..headers['Content-Type'] = 'application/json'
      ..body = jsonEncode(outletData);

    try {
      final response = await http.Response.fromStream(await request.send());
      if (mounted) {
        if (response.statusCode == 200 || response.statusCode == 201) {
          widget.onSave(); // Call onSave callback to refresh parent list
          Navigator.of(context).pop(); // Close the dialog
        } else {
            final error = jsonDecode(response.body)['error'];
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $error'), backgroundColor: Colors.red));
          }
        }
    } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Network Error: $e'), backgroundColor: Colors.red));
    } finally {
        if (mounted) setState(() => _isSaving = false); // End saving state
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEditing ? 'Edit Outlet' : 'Add Outlet'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Outlet name input field
            TextFormField(controller: _nameController, decoration: const InputDecoration(labelText: 'Outlet Name'), validator: (v) => v!.isEmpty ? 'Required' : null),
            const SizedBox(height: 8),
            // Phone number input field
            TextFormField(controller: _phoneController, decoration: const InputDecoration(labelText: 'Phone Number'), keyboardType: TextInputType.phone, validator: (v) => v!.isEmpty ? 'Required' : null),
            const SizedBox(height: 16),
            // Dropdown for outlet type
            DropdownButtonFormField<String>(
              value: _outletType,
              decoration: const InputDecoration(labelText: 'Outlet Type', border: OutlineInputBorder()),
              items: const [
                DropdownMenuItem(value: 'sales', child: Text('Sales Outlet')),
                DropdownMenuItem(value: 'production', child: Text('Production Unit')),
              ],
              onChanged: (value) => setState(() => _outletType = value!),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(onPressed: _isSaving ? null : _saveOutlet, child: _isSaving ? const CircularProgressIndicator() : const Text('Save')),
      ],
    );
  }
}

// ===================================================================
// OwnerBotChat Screen - Text-based chat with the OwnerBot
// ===================================================================
class OwnerBotChat extends StatefulWidget {
  const OwnerBotChat({super.key});
  @override
  _OwnerBotChatState createState() => _OwnerBotChatState();
}

class _OwnerBotChatState extends State<OwnerBotChat> {
  final TextEditingController _controller = TextEditingController(); // Controller for text input
  final ScrollController _scrollController = ScrollController(); // Controller for scrolling chat messages
  final SpeechToText _speechToText = SpeechToText(); // Speech-to-Text instance
  
  List<Map<String, String>> messages = []; // List to store chat messages
  bool _isLoading = false; // Loading state for bot response
  bool _speechEnabled = false; // Indicates if speech recognition is available
  bool _showSendButton = false; // Controls visibility of send button vs mic button

  @override
  void initState() {
    super.initState();
    _initSpeech(); // Initialize speech recognition
    // Listener to show/hide send button based on text input
    _controller.addListener(() {
      if (_controller.text.isNotEmpty != _showSendButton) {
        setState(() { _showSendButton = _controller.text.isNotEmpty; });
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _speechToText.stop(); // Stop speech recognition when disposing
    super.dispose();
  }

  // Initializes speech recognition service
  void _initSpeech() async {
    _speechEnabled = await _speechToText.initialize(); // Initialize and check availability
    setState(() {});
  }

  // Starts listening for speech input
  void _startListening() {
    if (!_speechEnabled || _speechToText.isListening) return; // Only listen if enabled and not already listening
    _speechToText.listen(
      onResult: (result) => setState(() => _controller.text = result.recognizedWords), // Update text field with recognized words
      localeId: "ml_IN", // Specify Malayalam (India) locale
    );
    setState(() {});
  }

  // Stops listening for speech input
  void _stopListening() {
    if (_speechToText.isListening) {
      _speechToText.stop();
      setState(() {});
    }
  }

  // Shows a SnackBar message
  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message), backgroundColor: isError ? Colors.red : null));
  }

  // Scrolls the chat messages to the bottom
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) _scrollController.animateTo(_scrollController.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    });
  }
  
  // Sends a message to the OwnerBot backend
  Future<void> sendMessage(String msg) async {
    if (msg.trim().isEmpty) return; // Don't send empty messages
    FocusScope.of(context).unfocus(); // Dismiss keyboard
    setState(() {
      messages.add({'sender': 'You', 'text': msg.trim()}); // Add user message to chat
      _isLoading = true; // Set loading state
    });
    _controller.clear(); // Clear input field
    _scrollToBottom(); // Scroll to bottom

    try {
      final response = await http.post(
        Uri.parse('$API_BASE_URL/ownerbot/ask/'), // Backend endpoint for bot interaction
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question': msg.trim(), 'mode': 'text'}), // Send text question
      );

      String botTextReply;
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        botTextReply = data['text_response'] ?? "No text answer received."; // Get bot's text response
      } else {
        botTextReply = 'Server error: ${response.statusCode}.'; // Handle server error
      }

      setState(() => messages.add({'sender': 'OwnerBot', 'text': botTextReply})); // Add bot's response to chat
    } catch (e) {
      _showSnackBar('Network Error: Could not connect to server.', isError: true);
      setState(() => messages.add({'sender': 'OwnerBot', 'text': 'Network Error.'})); // Handle network error
    } finally {
      if(mounted) {
        setState(() => _isLoading = false); // End loading state
        _scrollToBottom(); // Scroll to bottom again
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.background,
      body: Column(
        children: [
          Expanded(
            child: ListView.builder( // Display chat messages
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final message = messages[index];
                return MessageBubble(message: message['text']!, isUser: message['sender'] == 'You'); // Display message bubbles
              },
            ),
          ),
          if (_isLoading) const Padding(padding: EdgeInsets.all(8.0), child: LinearProgressIndicator()), // Show progress indicator when loading
          _buildMessageInput(), // Message input area
        ],
      ),
    );
  }

  // Builds the message input area with text field and buttons
  Widget _buildMessageInput() {
    return Container(
      padding: const EdgeInsets.all(8.0),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), spreadRadius: 1, blurRadius: 5)],
      ),
      child: Row(
        children: [
          // Button to launch dedicated Voice Chat Screen
          IconButton(
            icon: Icon(Icons.headset_mic, color: Theme.of(context).colorScheme.primary),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (context) => const VoiceChatScreen())),
            tooltip: 'Launch Voice Assistant',
          ),
          Expanded(
            child: TextField( // Text input field
              controller: _controller,
              onSubmitted: sendMessage, // Send message on submit
              decoration: const InputDecoration.collapsed(hintText: 'Type or use mic...'),
            ),
          ),
          // Dynamic button: Send if text is present, else mic for speech-to-text
          IconButton(
            icon: Icon(_showSendButton ? Icons.send : Icons.mic, color: Theme.of(context).colorScheme.primary),
            onPressed: _isLoading ? null : (_showSendButton ? () => sendMessage(_controller.text) : (_speechToText.isListening ? _stopListening : _startListening)),
            tooltip: _showSendButton ? 'Send Message' : 'Use Speech-to-Text',
          ),
        ],
      ),
    );
  }
}

// --- DEDICATED FULL-SCREEN VOICE CHAT SCREEN ---
// Enum to represent different states of the voice chat
enum VoiceChatState { idle, listening, processing, speaking }

class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key});
  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

class _VoiceChatScreenState extends State<VoiceChatScreen> with SingleTickerProviderStateMixin {
  final SpeechToText _speechToText = SpeechToText(); // Speech-to-Text instance
  final AudioPlayer _audioPlayer = AudioPlayer(); // Audio player instance
  VoiceChatState _currentState = VoiceChatState.idle; // Current state of voice chat
  String _statusText = "Tap the mic to start"; // Status text displayed to user
  String _lastRecognizedWords = ""; // Last recognized speech
  late AnimationController _pulseController; // Animation controller for mic button pulse

  @override
  void initState() {
    super.initState();
    // Initialize pulse animation for the mic button
    _pulseController = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000))..repeat(reverse: true);
    _initSpeech(); // Initialize speech recognition
    // Listen for audio player state changes to restart listening after bot speaks
    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (state == PlayerState.completed && mounted) {
        _startListening();
      }
    });
  }

  @override
  void dispose() {
    _speechToText.stop(); // Stop speech recognition
    _audioPlayer.dispose(); // Dispose audio player
    _pulseController.dispose(); // Dispose animation controller
    super.dispose();
  }

  // Initializes speech recognition, handling errors and status updates
  void _initSpeech() async {
    try {
      await _speechToText.initialize(
        onError: (error) => _handleError("Speech recognition error: ${error.errorMsg}"),
        onStatus: (status) {
          if (status == 'notListening' && _currentState == VoiceChatState.listening) {
            _stopListeningAndProcess(); // Automatically stop and process if not listening
          }
        });
    } catch (e) {
      _handleError("Error initializing speech recognition: $e");
    }
  }

  // Starts listening for speech input
  void _startListening() {
    if (!_speechToText.isAvailable || _speechToText.isListening || !mounted) return; // Check availability and state
    setState(() {
      _currentState = VoiceChatState.listening; // Set state to listening
      _statusText = "Listening..."; // Update status text
      _lastRecognizedWords = ""; // Clear last recognized words
    });
    _speechToText.listen(
      onResult: _onSpeechResult, // Callback for speech results
      localeId: "ml_IN", // Specify Malayalam (India) locale for better recognition
      pauseFor: const Duration(seconds: 2), // Pause before final result
      listenFor: const Duration(minutes: 1), // Max listening duration
    );
  }
  
  // Manually stops listening (e.g., when user taps mic button again)
  void _manualStopListening() {
    if (_speechToText.isListening) {
      _speechToText.stop();
    } else {
      _stopListeningAndProcess(); // If not listening, just process
    }
  }
  
  // Stops listening and processes the recognized speech
  void _stopListeningAndProcess() {
    if (_lastRecognizedWords.isNotEmpty) {
      if(mounted) setState(() { _currentState = VoiceChatState.processing; _statusText = "Thinking..."; }); // Set processing state
      _sendMessage(_lastRecognizedWords); // Send message to bot
    } else {
      if(mounted) setState(() => _currentState = VoiceChatState.idle); // Go back to idle if no words recognized
    }
  }

  // Callback for speech recognition results
  void _onSpeechResult(SpeechRecognitionResult result) {
    if(mounted) setState(() => _lastRecognizedWords = result.recognizedWords); // Update recognized words
    if (result.finalResult) {
      _stopListeningAndProcess(); // Process if it's the final result
    }
  }

  // Sends the recognized message to the OwnerBot backend for a voice response
  Future<void> _sendMessage(String msg) async {
    if (!mounted) return;
    setState(() { _currentState = VoiceChatState.processing; _statusText = "Getting response..."; }); // Set processing state
    try {
      final response = await http.post(
        Uri.parse('$API_BASE_URL/ownerbot/ask/'), // Backend endpoint
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question': msg.trim(), 'mode': 'voice'}), // Request voice response
      );
      if (!mounted) return;
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final audioData = data['audio_response']; // Base64 encoded audio
        final textResponse = data['text_response'] ?? 'No text response'; // Text response
        if (audioData != null && audioData.isNotEmpty) {
          setState(() { _currentState = VoiceChatState.speaking; _statusText = textResponse; }); // Set speaking state
          await _playAudio(audioData); // Play the audio response
        } else { _handleError("Received response with no audio."); } // Handle no audio
      } else { _handleError("Server error: ${response.statusCode}"); } // Handle server error
    } catch (e) {
      _handleError("Network Error: $e"); // Handle network error
    }
  }

  // Plays base64 encoded audio
  Future<void> _playAudio(String base64Audio) async {
    try {
      await _audioPlayer.play(BytesSource(base64.decode(base64Audio))); // Decode and play audio
    } catch (e) { _handleError("Could not play audio."); } // Handle audio playback error
  }

  // Handles and displays errors
  void _handleError(String errorMsg) {
    print(errorMsg); // Print error to console
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorMsg), backgroundColor: Colors.red)); // Show snackbar
      setState(() { _currentState = VoiceChatState.idle; _statusText = "Tap the mic to start"; }); // Reset to idle
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black, // Dark background for voice chat
      appBar: AppBar(
        backgroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(icon: const Icon(Icons.close, color: Colors.white), onPressed: () => Navigator.of(context).pop()), // Close button
      ),
      body: Center(
        child: Column(
          children: [
            const Spacer(flex: 2),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24.0),
              child: Text(
                _currentState == VoiceChatState.listening && _lastRecognizedWords.isNotEmpty ? _lastRecognizedWords : _statusText,
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w500),
              ),
            ),
            const Spacer(flex: 1),
            _buildMicButton(), // Mic button
            const Spacer(flex: 2),
          ],
        ),
      ),
    );
  }

  // Builds the dynamic mic button based on current state
  Widget _buildMicButton() {
    IconData icon;
    Color buttonColor;
    bool isProcessing = _currentState == VoiceChatState.processing;
    switch (_currentState) {
      case VoiceChatState.listening: buttonColor = Colors.blue.shade700; icon = Icons.mic; break;
      case VoiceChatState.speaking: buttonColor = Colors.green.shade700; icon = Icons.graphic_eq; break;
      case VoiceChatState.processing: buttonColor = Colors.orange.shade700; icon = Icons.settings_ethernet; break;
      default: buttonColor = Colors.grey.shade800; icon = Icons.mic_none; break;
    }
    return GestureDetector(
      onTap: () {
        if (_currentState == VoiceChatState.idle) {
          _startListening(); // Start listening from idle
        } else if (_currentState == VoiceChatState.listening) {
          _manualStopListening(); // Manually stop listening
        }
      },
      child: AnimatedContainer( // Animated container for visual feedback
        duration: const Duration(milliseconds: 300),
        width: 120, height: 120,
        decoration: BoxDecoration(
          color: buttonColor,
          shape: BoxShape.circle,
          boxShadow: [ BoxShadow(color: buttonColor.withOpacity(0.5), blurRadius: _currentState == VoiceChatState.listening ? 25 : 10, spreadRadius: _currentState == VoiceChatState.listening ? 10 : 3) ],
        ),
        child: Center(
          child: isProcessing ? const CircularProgressIndicator(color: Colors.white, strokeWidth: 5) : Icon(icon, color: Colors.white, size: 60),
        )
      ),
    );
  }
}

// --- Other Utility Classes ---
// Message bubble for chat display
class MessageBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  const MessageBubble({super.key, required this.message, required this.isUser});
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Card(
        color: isUser ? Theme.of(context).colorScheme.primary : Theme.of(context).colorScheme.surface,
        elevation: 3,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(15), topRight: const Radius.circular(15),
            bottomLeft: isUser ? const Radius.circular(15) : const Radius.circular(4),
            bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(15),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Text(message, style: TextStyle(color: isUser ? Colors.white : Colors.black87, fontSize: 16)),
        ),
      ),
    );
  }
}

// ===================================================================
// ProductManagementScreen - Manages products (add, edit, delete, search)
// ===================================================================
class ProductManagementScreen extends StatefulWidget {
  const ProductManagementScreen({super.key});
  @override
  _ProductManagementScreenState createState() => _ProductManagementScreenState();
}

class _ProductManagementScreenState extends State<ProductManagementScreen> {
  List<dynamic> _allProducts = []; // All products fetched
  List<dynamic> _filteredProducts = []; // Products filtered by search
  bool _isLoading = true; // Loading state
  String _error = ''; // Error message
  final TextEditingController _searchController = TextEditingController(); // Search input controller

  @override
  void initState() {
    super.initState();
    _fetchProducts(); // Fetch products on init
    _searchController.addListener(_filterProducts); // Listen for search input changes
  }
  
  @override
  void dispose() {
    _searchController.removeListener(_filterProducts);
    _searchController.dispose();
    super.dispose();
  }

  // Fetches all products from the backend
  Future<void> _fetchProducts() async {
    setState(() { _isLoading = true; _error = ''; }); // Set loading state
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/items/manage-products/'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _allProducts = jsonDecode(utf8.decode(response.bodyBytes)); // Parse all products
            _filteredProducts = _allProducts; // Initialize filtered list with all products
            _isLoading = false; // End loading
          });
        }
      } else {
        throw Exception('Failed to load products'); // Throw error
      }
    } catch (e) {
      if (mounted) setState(() { _error = 'Failed to load products: $e'; _isLoading = false; }); // Set error state
    }
  }

  // Filters products based on search query
  void _filterProducts() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredProducts = _allProducts.where((product) {
        final productName = (product['name'] as String?)?.toLowerCase() ?? '';
        return productName.contains(query);
      }).toList();
    });
  }

  // Deletes a product by its ID
  void _deleteProduct(String productId, String productName) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete "$productName"?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Delete', style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm != true) return; // If user cancels, do nothing

    try {
      final response = await http.delete(Uri.parse('$API_BASE_URL/items/manage-products/$productId/')); // Send DELETE request
      if (response.statusCode == 204) { // 204 No Content indicates successful deletion
        _showSnackBar('Product deleted successfully');
        _fetchProducts(); // Refresh the list after deletion
      } else {
        throw Exception('Failed to delete product. Server responded with status ${response.statusCode}');
      }
    } catch (e) {
      _showSnackBar('Error deleting product: $e', isError: true);    
    }
  }

  // Shows the product dialog for adding or editing a product
  void _showProductDialog({Map<String, dynamic>? product}) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _ProductDialog(product: product, onSave: _fetchProducts), // Pass product for editing, onSave to refresh list
    );
  }
  
  // Shows a SnackBar message
  void _showSnackBar(String message, {bool isError = false}) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
      ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator( // Pull to refresh functionality
        onRefresh: _fetchProducts,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: TextField( // Search input field
                controller: _searchController,
                decoration: InputDecoration(labelText: 'Search Products', prefixIcon: const Icon(Icons.search)),
              ),
            ),
            // Conditional display for loading/error/list
            if (_isLoading)
              const Expanded(child: Center(child: CircularProgressIndicator()))
            else if (_error.isNotEmpty)
              Expanded(child: Center(child: Text(_error)))
            else if (_filteredProducts.isEmpty)
              const Expanded(child: Center(child: Text('No products found.')))
            else
              Expanded(
                child: ListView.builder( // Display products in a list
                  padding: const EdgeInsets.only(bottom: 80),
                  itemCount: _filteredProducts.length,
                  itemBuilder: (context, index) {
                    final product = _filteredProducts[index];
                    final imageUrl = product['image_url']; // Get image URL
                    final productType = product['type'] ?? 'production';
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar( // Product image or placeholder
                          backgroundImage: (imageUrl != null && imageUrl.isNotEmpty) ? NetworkImage(imageUrl) : null,
                          child: (imageUrl == null || imageUrl.isEmpty) ? Text(product['name']?[0] ?? 'P') : null,
                        ),
                        title: Text(product['name'] ?? 'No Name', style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text('Type: ${_toTitleCase(productType)} | Stock: ${product['stock']}'),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(icon: const Icon(Icons.edit, color: Colors.blue), onPressed: () => _showProductDialog(product: product)), // Edit button
                            IconButton(icon: const Icon(Icons.delete, color: Colors.red), onPressed: () => _deleteProduct(product['id'], product['name'])), // Delete button
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton( // Button to add new product
        onPressed: () => _showProductDialog(),
        tooltip: 'Add Product',
        child: const Icon(Icons.add),
      ),
    );
  }
}

// --- Dialog for Adding/Editing Products ---
class _ProductDialog extends StatefulWidget {
  final Map<String, dynamic>? product; // Product data for editing (null for new)
  final VoidCallback onSave; // Callback to refresh list after save
  const _ProductDialog({this.product, required this.onSave});
  @override
  _ProductDialogState createState() => _ProductDialogState();
}

class _ProductDialogState extends State<_ProductDialog> {
  final _formKey = GlobalKey<FormState>(); // Form key for validation
  late TextEditingController _nameController, _priceController, _stockController, _thresholdController, _barcodeController, _costPriceController; // Text controllers
  String _unitType = 'piece'; // Product unit type
  String _productType = 'production'; // Product type (production/wholesale)
  XFile? _imageFile; // Selected image file
  String? _existingImageUrl; // Existing image URL
  bool _isSaving = false; // Saving state
  bool _isGeneratingBarcode = false; // State for barcode generation loading
  bool get _isEditing => widget.product != null; // Check if in editing mode

  @override
  void initState() {
    super.initState();
    // Initialize controllers with existing data if editing
    _nameController = TextEditingController(text: widget.product?['name'] ?? '');
    _priceController = TextEditingController(text: widget.product?['price']?.toString() ?? '');
    _stockController = TextEditingController(text: widget.product?['stock']?.toString() ?? '');
    _thresholdController = TextEditingController(text: widget.product?['low_stock_threshold']?.toString() ?? '10');
    _barcodeController = TextEditingController(text: widget.product?['barcode'] ?? '');
    _costPriceController = TextEditingController(text: widget.product?['cost_price']?.toString() ?? '');
    _unitType = widget.product?['unit_type'] ?? 'piece';
    _productType = widget.product?['type'] ?? 'production';
    _existingImageUrl = widget.product?['image_url'];
  }

  @override
  void dispose() {
    _nameController.dispose();
    _priceController.dispose();
    _stockController.dispose();
    _thresholdController.dispose();
    _barcodeController.dispose();
    _costPriceController.dispose();
    super.dispose();
  }

  // Generates a unique barcode from the backend
  Future<void> _generateBarcode() async {
    setState(() => _isGeneratingBarcode = true); // Set loading state
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/items/generate-barcode/'));
      if(mounted && response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _barcodeController.text = data['barcode']; // Set generated barcode
        });
      } else {
        throw Exception('Failed to generate barcode'); // Throw error
      }
    } catch(e) {
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red));
    } finally {
      if(mounted) setState(() => _isGeneratingBarcode = false); // End loading state
    }
  }

  // Picks an image from camera or gallery
  Future<void> _pickImage(ImageSource source) async {
    final pickedFile = await ImagePicker().pickImage(source: source, imageQuality: 50); // Pick image with compression
    if (pickedFile != null) setState(() => _imageFile = pickedFile); // Set selected image
  }

  // Uploads the selected image to the backend
  Future<String?> _uploadImage(XFile imageFile) async {
    var request = http.MultipartRequest('POST', Uri.parse('$API_BASE_URL/items/upload-image/'));
    // Add the image file to the request
    request.files.add(await http.MultipartFile.fromPath('file', imageFile.path, contentType: MediaType('image', 'jpeg'))); 
    try {
      var response = await http.Response.fromStream(await request.send());
      if (response.statusCode == 201) return jsonDecode(response.body)['image_url']; // Return image URL on success
    } catch (e) { print("Image upload failed: $e"); }
    return null; // Return null on failure
  }

  // Saves (adds or updates) the product to the backend
  Future<void> _saveProduct() async {
    if (!_formKey.currentState!.validate() || _isSaving) return; // Validate form and check saving state
    setState(() => _isSaving = true); // Set saving state
    
    String? finalImageUrl = _existingImageUrl; // Start with existing URL
    if (_imageFile != null) { // If a new image is selected, upload it
      finalImageUrl = await _uploadImage(_imageFile!);
      if (finalImageUrl == null) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Image upload failed!'), backgroundColor: Colors.red));
        setState(() => _isSaving = false);
        return;
      }
    }

    // Prepare product data payload
    final Map<String, dynamic> productData = {
      'name': _nameController.text,
      'price': double.tryParse(_priceController.text) ?? 0.0,
      'stock': int.tryParse(_stockController.text) ?? 0,
      'unit_type': _unitType,
      'low_stock_threshold': int.tryParse(_thresholdController.text) ?? 10,
      'barcode': _barcodeController.text.isNotEmpty ? _barcodeController.text : null,
      'type': _productType,
      'cost_price': double.tryParse(_costPriceController.text) ?? 0.0,
      'image_url': finalImageUrl,
    };

    // Determine URL and HTTP method based on editing or adding
    final url = _isEditing ? '$API_BASE_URL/items/manage-products/${widget.product!['id']}/' : '$API_BASE_URL/items/manage-products/';
    final method = _isEditing ? 'PUT' : 'POST';
    
    try {
        final request = http.Request(method, Uri.parse(url))
            ..headers['Content-Type'] = 'application/json'
            ..body = jsonEncode(productData);
        final response = await http.Response.fromStream(await request.send());
        if(mounted) {
            if (response.statusCode == 200 || response.statusCode == 201) {
                // If it's a wholesale product, record its cost as an expense
                // This assumes your backend's profit/loss report will *not* double-count this
                // as COGS when the item is sold.
                if (_productType == 'wholesale') {
                  final double cost = double.tryParse(_costPriceController.text) ?? 0.0;
                  final int quantity = int.tryParse(_stockController.text) ?? 0;
                  final double totalWholesaleExpense = cost * quantity;
                  await _recordWholesaleExpense(totalWholesaleExpense, _nameController.text);
                }

                widget.onSave(); // Call onSave callback to refresh parent list
                Navigator.of(context).pop(); // Close the dialog
            } else {
                final error = jsonDecode(response.body)['error'];
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $error'), backgroundColor: Colors.red));
            }
        }
    } catch(e) {
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Network error: $e')));
    } finally {    
        if (mounted) setState(() => _isSaving = false); // End saving state
    }
  }

  // Records a wholesale purchase as an expense in the backend
  Future<void> _recordWholesaleExpense(double amount, String productName) async {
    final expenseData = {
      'description': 'Wholesale purchase: $productName',
      'amount': amount,
      'category': 'Raw Materials', // Categorize as Raw Materials or a specific wholesale category
      'date': DateFormat('yyyy-MM-dd').format(DateTime.now()),
    };

    try {
      final response = await http.post(
        Uri.parse('$API_BASE_URL/expenses/manage/'), // Backend expense endpoint
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(expenseData),
      );
      if (response.statusCode == 201) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Wholesale expense recorded!'), backgroundColor: Colors.green));
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to record wholesale expense: ${response.body}'), backgroundColor: Colors.orange));
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error recording wholesale expense: $e'), backgroundColor: Colors.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEditing ? 'Edit Product' : 'Add Product'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Image display area
              if (_imageFile != null)
                kIsWeb // Handle web image display from XFile path
                    ? Image.network(_imageFile!.path, height: 100, width: 100, fit: BoxFit.cover)
                    : Image.file(File(_imageFile!.path), height: 100, width: 100, fit: BoxFit.cover)
              else if (_existingImageUrl != null && _existingImageUrl!.isNotEmpty)
                Image.network(_existingImageUrl!, height: 100, width: 100, fit: BoxFit.cover),
              
              const SizedBox(height: 16),
              // Image picking buttons (Camera/Gallery)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  ElevatedButton.icon(
                    onPressed: () => _pickImage(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Take Photo'),
                  ),
                  ElevatedButton.icon(
                    onPressed: () => _pickImage(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library),
                    label: const Text('Choose Image'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              
              // Product form fields
              TextFormField(controller: _nameController, decoration: const InputDecoration(labelText: 'Name'), validator: (v) => v!.isEmpty ? 'Required' : null),
              const SizedBox(height: 8),
              TextFormField(controller: _priceController, decoration: const InputDecoration(labelText: 'Selling Price (per unit)'), keyboardType: TextInputType.number, validator: (v) => v!.isEmpty ? 'Required' : null),
              const SizedBox(height: 8),
              TextFormField(controller: _stockController, decoration: const InputDecoration(labelText: 'Stock'), keyboardType: TextInputType.number, validator: (v) => v!.isEmpty ? 'Required' : null),
              const SizedBox(height: 8),
              TextFormField(controller: _thresholdController, decoration: const InputDecoration(labelText: 'Low Stock Threshold'), keyboardType: TextInputType.number, validator: (v) => v!.isEmpty ? 'Required' : null),
              const SizedBox(height: 8),
              TextFormField( // Barcode input with generate button
                controller: _barcodeController,
                decoration: InputDecoration(
                  labelText: 'Barcode (optional)',
                  suffixIcon: _isGeneratingBarcode  
                    ? const Padding(padding: EdgeInsets.all(12.0), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))
                    : IconButton(
                        icon: const Icon(Icons.casino_outlined),
                        tooltip: 'Generate Barcode',
                        onPressed: _generateBarcode,
                      ),
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>( // Unit type dropdown
                value: _unitType,
                decoration: const InputDecoration(labelText: 'Selling Unit'),
                items: const [
                  DropdownMenuItem(value: 'piece', child: Text('Per Piece')),
                  DropdownMenuItem(value: 'kg', child: Text('Per Kg'))
                ],
                onChanged: (value) => setState(() => _unitType = value!),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>( // Product type dropdown
                value: _productType,
                decoration: const InputDecoration(labelText: 'Product Type'),
                items: const [
                  DropdownMenuItem(value: 'production', child: Text('Production (Made In-House)')),
                  DropdownMenuItem(value: 'wholesale', child: Text('Wholesale (Bought & Resold)'))
                ],
                onChanged: (value) => setState(() => _productType = value!),
              ),
              // Cost Price field only for wholesale products
              if (_productType == 'wholesale') ...[
                const SizedBox(height: 8),
                TextFormField(
                  controller: _costPriceController,
                  decoration: const InputDecoration(labelText: 'Cost Price (Purchase Price)'),
                  keyboardType: TextInputType.number,
                  validator: (v) => (_productType == 'wholesale' && v!.isEmpty) ? 'Required' : null
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(onPressed: _isSaving ? null : _saveProduct, child: _isSaving ? const CircularProgressIndicator() : const Text('Save')),
      ],
    );
  }
}

// --- Sales Reporter Screen ---
class SalesReporterScreen extends StatefulWidget {
  const SalesReporterScreen({super.key});
  @override
  State<SalesReporterScreen> createState() => _SalesReporterScreenState();
}

class _SalesReporterScreenState extends State<SalesReporterScreen> {
  String _salesReportText = 'Loading...'; // Text summary of sales
  List<dynamic> _salesData = []; // Structured sales data (e.g., for charts, though not used for chart here)
  bool _isLoading = true; // Loading state
  DateTime? _startDate; // Start date for report
  DateTime? _endDate; // End date for report
  
  List<dynamic> _outletsList = []; // List of outlets for filtering
  String? _selectedOutletId; // Currently selected outlet ID
  bool _isOutletsLoading = true; // Loading state for outlets

  // Colors for potential pie chart (not used in current build but kept from original)
  final List<Color> pieColors = [
    Colors.blue.shade300, Colors.green.shade300, Colors.orange.shade300,
    Colors.purple.shade300, Colors.red.shade300, Colors.teal.shade300,
    Colors.pink.shade300, Colors.indigo.shade300,
  ];

  @override
  void initState() {
    super.initState();
    // Default date range: last 7 days
    _startDate = DateTime.now().subtract(const Duration(days: 6));
    _endDate = DateTime.now();
    _fetchOutletsAndInitialReport(); // Fetch outlets and then the report
  }

  // Fetches outlets first, then the sales report
  Future<void> _fetchOutletsAndInitialReport() async {
    setState(() { _isOutletsLoading = true; }); // Set outlets loading
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/outlets/manage/'));
      if (mounted) {
        if (response.statusCode == 200) {
          final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
          setState(() {
            _outletsList = data.map((json) => {'id': json['id'], 'name': json['name']}).toList(); // Extract ID and Name
            _outletsList.insert(0, {'id': 'All Outlets', 'name': 'All Outlets'}); // Add "All Outlets" option
            _selectedOutletId = _outletsList[0]['id']; // Select "All Outlets" by default
            _isOutletsLoading = false; // End outlets loading
          });
          _fetchReports(); // Fetch sales reports after outlets are loaded
        } else {
          throw Exception('Failed to load outlets'); // Throw error
        }
      }
    } catch (e) {
      if (mounted) {
        _showSnackBar('Error fetching outlets: $e', isError: true);
        setState(() { _isOutletsLoading = false; });
      }
    }
  }

  // Shows a date range picker
  Future<void> _selectDateRange(BuildContext context) async {
    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2023, 1),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDateRange: DateTimeRange(start: _startDate!, end: _endDate!),
    );
    if (picked != null && (picked.start != _startDate || picked.end != _endDate)) {
      setState(() {
        _startDate = picked.start;
        _endDate = picked.end;
      });
      _fetchReports(); // Fetch reports with new dates
    }
  }

  // Fetches structured and summary sales reports from the backend
  Future<void> _fetchReports() async {
    if (_selectedOutletId == null) return; // Don't fetch if no outlet selected
    setState(() { _isLoading = true; }); // Set loading state
    try {
      Map<String, String> queryParams = {
        'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
        'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
      };
      if (_selectedOutletId != 'All Outlets') {
        queryParams['outlet_id'] = _selectedOutletId!; // Add outlet filter if not "All"
      }

      // Prepare URIs for structured and summary reports
      final structuredUri = Uri.parse('$API_BASE_URL/sales/structured-report/').replace(queryParameters: queryParams);
      final textUri = Uri.parse('$API_BASE_URL/sales/summary-report/').replace(queryParameters: queryParams);

      // Fetch both reports concurrently
      final responses = await Future.wait([http.get(structuredUri), http.get(textUri)]);
      
      final structuredResponse = responses[0];
      final textResponse = responses[1];
      
      if (mounted) {
        setState(() {
          // Process structured report response
          if (structuredResponse.statusCode == 200) {
            _salesData = jsonDecode(utf8.decode(structuredResponse.bodyBytes));
          } else {
            _salesData = [];
            _showSnackBar('Error fetching chart data: ${structuredResponse.statusCode}', isError: true);
          }

          // Process text summary report response
          if (textResponse.statusCode == 200) {
            _salesReportText = jsonDecode(utf8.decode(textResponse.bodyBytes))['report'] ?? 'N/A';
          } else {
            _salesReportText = 'Error fetching text report: ${textResponse.statusCode}';
          }
        });
      }
    } catch (e) {
      if (mounted) _showSnackBar('Network error fetching sales data: $e', isError: true);
    } finally {
      if (mounted) setState(() { _isLoading = false; }); // End loading
    }
  }

  // Deletes sales data for the current report's date and outlet range
  Future<void> _deleteCurrentReport() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete all sales data for "${_toTitleCase(_outletsList.firstWhere((o) => o['id'] == _selectedOutletId)['name'])}" from ${DateFormat.yMMMd().format(_startDate!)} to ${DateFormat.yMMMd().format(_endDate!)}? This action cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('DELETE', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return; // If user cancels, do nothing

    setState(() { _isLoading = true; }); // Set loading state
    try {
      Map<String, String> queryParams = {
        'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
        'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
      };
      if (_selectedOutletId != 'All Outlets') {
        queryParams['outlet_id'] = _selectedOutletId!; // Add outlet filter if not "All"
      }
      
      final deleteUri = Uri.parse('$API_BASE_URL/sales/delete-range/').replace(queryParameters: queryParams);
      final response = await http.delete(deleteUri); // Send DELETE request

      if (mounted) {
        if (response.statusCode == 200) {
          final data = jsonDecode(utf8.decode(response.bodyBytes));
          _showSnackBar(data['message'] ?? 'Deletion successful!', isError: false);
          _fetchReports(); // Refresh reports after deletion
        } else {
          final error = jsonDecode(utf8.decode(response.bodyBytes))['error'];
          _showSnackBar('Error deleting report: $error', isError: true);
        }
      }
    } catch (e) {
      if(mounted) _showSnackBar('Network error during deletion: $e', isError: true);
    } finally {
      if(mounted) setState(() { _isLoading = false; }); // End loading
    }
  }

  // Copies the sales report text to clipboard
  void _downloadReport() {
    Clipboard.setData(ClipboardData(text: _salesReportText)); // Copy to clipboard
    _showSnackBar('Report copied to clipboard!', isError: false);
  }

  // Shows a SnackBar message
  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
    ));
  }

  @override
  Widget build(BuildContext context) {
    // This part is for potential product sales quantities for a chart,
    // but the current UI only displays the text report.
    Map<String, double> productSalesQuantities = {};
    for (var sale in _salesData) {
      if (sale['items'] is List) {
        for (var item in sale['items']) {
          if (item['product_id'] != null) {
            String itemId = item['product_id'];
            double quantity = (item['quantity'] as num?)?.toDouble() ?? 0.0;
            productSalesQuantities.update(itemId, (value) => value + quantity, ifAbsent: () => quantity);
          }
        }
      }
    }

    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Daily Sales Summary', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary)),
            const SizedBox(height: 16),
            // Date range and outlet filter row
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _selectDateRange(context),
                    icon: const Icon(Icons.calendar_today),
                    label: Text(_startDate == null ? 'Select Dates' : '${DateFormat('MMM d').format(_startDate!)} - ${DateFormat('MMM d').format(_endDate!)}'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _selectedOutletId,
                    isExpanded: true,
                    decoration: const InputDecoration(border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 10)),
                    items: _outletsList.map<DropdownMenuItem<String>>((outlet) {
                      return DropdownMenuItem<String>(
                        value: outlet['id'],
                        child: Text(_toTitleCase(outlet['name']), overflow: TextOverflow.ellipsis),
                      );
                    }).toList(),
                    onChanged: _isOutletsLoading ? null : (String? newValue) {
                      setState(() { _selectedOutletId = newValue!; });
                      _fetchReports(); // Fetch reports with new outlet filter
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // Conditional display for loading/report text
            _isLoading
                ? const Expanded(child: Center(child: CircularProgressIndicator()))
                : Expanded(
                    child: SingleChildScrollView(
                      child: Column(
                        children: [
                          Text('Detailed Sales Report (Text)', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          Card(
                            elevation: 2,
                            child: Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Text(_salesReportText, style: GoogleFonts.inter(fontSize: 16, color: Colors.black87)),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
            const SizedBox(height: 16),
            // Action buttons for refresh, copy, and delete
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : _fetchReports,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Refresh'),
                ),
                ElevatedButton.icon(
                  onPressed: _isLoading || _salesReportText.contains('Loading') ? null : _downloadReport,
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy'),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blue.shade700),
                ),
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : _deleteCurrentReport,
                  icon: const Icon(Icons.delete_forever),
                  label: const Text('Delete'),
                  style: ElevatedButton.styleFrom(backgroundColor: Theme.of(context).colorScheme.error),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class ProductionReporterScreen extends StatefulWidget {
  const ProductionReporterScreen({super.key});
  @override
  State<ProductionReporterScreen> createState() => _ProductionReporterScreenState();
}

class _ProductionReporterScreenState extends State<ProductionReporterScreen> {
  List<dynamic> _productionLogs = [];
  List<dynamic> _ingredients = [];
  List<dynamic> _productionUnits = [];
  String? _selectedUnitId;
  bool _isLoading = true;
  String _error = '';
  DateTime? _startDate;
  DateTime? _endDate;

  @override
  void initState() {
    super.initState();
    _startDate = DateTime.now().subtract(const Duration(days: 6));
    _endDate = DateTime.now();
    _fetchInitialData();
  }

  Future<void> _fetchInitialData() async {
    setState(() { _isLoading = true; _error = ''; });
    await _fetchOutlets();
    if (mounted && _selectedUnitId != null) {
      await _fetchReports();
    }
    if (mounted) {
      setState(() { _isLoading = false; });
    }
  }
  
  Future<void> _fetchOutlets() async {
    try {
        final response = await http.get(Uri.parse('$API_BASE_URL/outlets/manage/'));
        if (!mounted) return;
        if (response.statusCode == 200) {
            final allOutlets = jsonDecode(utf8.decode(response.bodyBytes));
            setState(() {
                _productionUnits = allOutlets.where((o) => o['type'] == 'production').toList();
                _productionUnits.insert(0, {'id': 'All Production Units', 'name': 'All Production Units'});
                if (_selectedUnitId == null && _productionUnits.isNotEmpty) {
                  _selectedUnitId = _productionUnits[0]['id'];
                }
            });
        } else {
          throw Exception('Failed to load outlets (${response.statusCode})');
        }
    } catch (e) {
      if (mounted) {
        _showSnackBar('Error loading production units: $e', isError: true);
        setState(() => _error = 'Could not load outlets.');
      }
    }
  }

  Future<void> _fetchReports() async {
    if (_selectedUnitId == null || _startDate == null || _endDate == null) {
        setState(() => _isLoading = false);
        return;
    }
    setState(() { _isLoading = true; _error = ''; });
    try {
      final queryParams = {
        'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
        'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
      };
      if (_selectedUnitId != 'All Production Units') {
        queryParams['production_unit_id'] = _selectedUnitId!;
      }
      
      final productionUri = Uri.parse('$API_BASE_URL/production/structured-report/').replace(queryParameters: queryParams);
      final ingredientsUri = Uri.parse('$API_BASE_URL/production/ingredients/all/');
      
      final responses = await Future.wait([
          http.get(productionUri), 
          http.get(ingredientsUri)
      ]);

      if (!mounted) return;

      final productionResponse = responses[0];
      final ingredientsResponse = responses[1];
      
      if (productionResponse.statusCode == 200) {
        _productionLogs = jsonDecode(utf8.decode(productionResponse.bodyBytes));
      } else {
         final errorBody = jsonDecode(utf8.decode(productionResponse.bodyBytes));
        _error += 'Failed to load production logs: ${errorBody['error'] ?? 'Unknown Error'}. ';
      }
      
      if (ingredientsResponse.statusCode == 200) {
        _ingredients = jsonDecode(utf8.decode(ingredientsResponse.bodyBytes));
      } else {
        _error += 'Failed to load ingredients. ';
      }
      setState(() {});

    } catch (e) {
      if(mounted) setState(() { _error = 'Network error: $e'; });
    } finally {
      if(mounted) setState(() { _isLoading = false; });
    }
  }
  
  Future<void> _selectDateRange(BuildContext context) async {
    final picked = await showDateRangePicker(
      context: context, 
      initialDateRange: DateTimeRange(start: _startDate!, end: _endDate!), 
      firstDate: DateTime(2023), 
      lastDate: DateTime.now().add(const Duration(days: 365))
    );
    if (picked != null) {
      setState(() { _startDate = picked.start; _endDate = picked.end; });
      _fetchReports();
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
    ));
  }

  void _copyReportToClipboard() {
    String reportText = "Production Report (${DateFormat.yMMMd().format(_startDate!)} - ${DateFormat.yMMMd().format(_endDate!)})\n";
    final unitName = _productionUnits.firstWhere((u) => u['id'] == _selectedUnitId, orElse: () => {'name': 'N/A'})['name'];
    reportText += "Unit: ${_toTitleCase(unitName ?? 'N/A')}\n\n";
    reportText += "--- Production Logs ---\n";
    if (_productionLogs.isNotEmpty) {
      for (var log in _productionLogs) {
        final timestampStr = log['timestamp'];
        final logDate = timestampStr != null ? DateTime.parse(timestampStr) : DateTime.now();
        reportText += "${_toTitleCase(log['recipe_id'] ?? 'Unknown')}: ${log['quantity_produced']} units on ${DateFormat.yMd().add_jm().format(logDate)}\n";
      }
    } else {
      reportText += "No logs in this period.\n";
    }
    
    reportText += "\n--- Current Ingredient Inventory ---\n";
    if (_ingredients.isNotEmpty) {
      for (var ing in _ingredients) {
        reportText += "${ing['name'] ?? 'Unnamed'}: ${ing['stock'] ?? 0} ${ing['unit'] ?? ''}\n";
      }
    } else {
      reportText += "No ingredients found.\n";
    }
    Clipboard.setData(ClipboardData(text: reportText));
    _showSnackBar("Report copied to clipboard!");
  }

  Future<void> _deleteProductionLogs() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete all production logs from ${DateFormat.yMMMd().format(_startDate!)} to ${DateFormat.yMMMd().format(_endDate!)} for the selected unit? This action CANNOT be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('DELETE', style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm != true) return;
    setState(() { _isLoading = true; });
    try {
      final queryParams = {
          'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
          'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
        };
      if (_selectedUnitId != null && _selectedUnitId != 'All Production Units') {
        queryParams['production_unit_id'] = _selectedUnitId!;
      }
      
      final deleteUri = Uri.parse('$API_BASE_URL/production/logs/delete-range/').replace(queryParameters: queryParams);
      final response = await http.delete(deleteUri);

      if (!mounted) return;
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        _showSnackBar(data['message'] ?? 'Deletion successful!');
        _fetchReports();
      } else {
        final error = jsonDecode(utf8.decode(response.bodyBytes))['error'];
        throw Exception(error);
      }
    } catch (e) {
      if (mounted) _showSnackBar('Error deleting logs: $e', isError: true);
    } finally {
      if (mounted) setState(() { _isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Production & Inventory',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            const SizedBox(height: 16),
            _buildFilterControls(),
            const SizedBox(height: 16),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _error.isNotEmpty
                      ? Center(child: Text(_error, style: const TextStyle(color: Colors.red, fontSize: 16), textAlign: TextAlign.center,))
                      : _buildReportLayout(),
            ),
          ],
        ),
      ),
      floatingActionButton: _buildFloatingActionButtons(),
    );
  }

  Widget _buildFilterControls() {
    return Row(
      children: [
        Expanded(
          flex: 3,
          child: ElevatedButton.icon(
            onPressed: () => _selectDateRange(context),
            icon: const Icon(Icons.calendar_today, size: 16),
            label: Text('${DateFormat('MMM d').format(_startDate!)} - ${DateFormat('MMM d, yyyy').format(_endDate!)}'),
            style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          flex: 2,
          child: DropdownButtonFormField<String>(
            value: _selectedUnitId,
            decoration: const InputDecoration(border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 10)),
            items: _productionUnits.map((unit) => DropdownMenuItem<String>(
              value: unit['id'],
              child: Text(_toTitleCase(unit['name']), overflow: TextOverflow.ellipsis),
            )).toList(),
            onChanged: (value) {
              if (value == null) return;
              setState(() => _selectedUnitId = value);
              _fetchReports();
            },
          ),
        ),
      ],
    );
  }

  Widget _buildReportLayout() {
    final isWideScreen = MediaQuery.of(context).size.width > 600;
    if (isWideScreen) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(flex: 2, child: _buildProductionLogList()),
          const VerticalDivider(width: 32, thickness: 1),
          Expanded(flex: 1, child: _buildIngredientList()),
        ],
      );
    } else {
      return DefaultTabController(
        length: 2,
        child: Column(
          children: [
            const TabBar(
              tabs: [
                Tab(text: 'Production Log'),
                Tab(text: 'Ingredient Stock'),
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  _buildProductionLogList(),
                  _buildIngredientList(),
                ],
              ),
            ),
          ],
        ),
      );
    }
  }

  Widget _buildProductionLogList() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0),
          child: Text("Production Log", style: Theme.of(context).textTheme.titleLarge),
        ),
        const Divider(),
        Expanded(
          child: _productionLogs.isEmpty
              ? const Center(child: Text('No production recorded in this period.'))
              : ListView.builder(
                  itemCount: _productionLogs.length,
                  itemBuilder: (context, index) {
                    final log = _productionLogs[index];
                    final recipeName = _toTitleCase(log['recipe_id']);
                    final quantity = log['quantity_produced'] ?? 0;
                    final unitName = _toTitleCase(log['production_unit_id']);
                    final logDate = log['timestamp'] != null ? DateTime.parse(log['timestamp']) : null;

                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(backgroundColor: Colors.brown.shade100, child: const Icon(Icons.bakery_dining, color: Colors.brown)),
                        title: Text('$recipeName x $quantity', style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text(
                          'Unit: $unitName\nOn: ${logDate != null ? DateFormat.yMd().add_jm().format(logDate) : 'No date'}',
                        ),
                        isThreeLine: true,
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildIngredientList() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0),
          child: Text("Ingredient Stock", style: Theme.of(context).textTheme.titleLarge),
        ),
        const Divider(),
        Expanded(
          child: _ingredients.isEmpty
              ? const Center(child: Text('No ingredients found.'))
              : ListView.builder(
                  itemCount: _ingredients.length,
                  itemBuilder: (context, index) {
                    final ing = _ingredients[index];
                    final stock = ing['stock'] ?? 0;
                    final unit = ing['unit'] ?? '';
                    final isLowStock = stock <= 5; // Example low stock threshold

                    return Card(
                      color: isLowStock ? Colors.orange.shade50 : Colors.green.shade50,
                      child: ListTile(
                        title: Text(ing['name'] ?? 'Unknown', style: const TextStyle(fontWeight: FontWeight.w500)),
                        trailing: Text(
                          '${stock.toStringAsFixed(2)} $unit',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildFloatingActionButtons() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        FloatingActionButton(
          onPressed: _isLoading ? null : _fetchInitialData,
          tooltip: 'Refresh',
          heroTag: 'refreshFab',
          child: const Icon(Icons.refresh),
        ),
        const SizedBox(height: 10),
        FloatingActionButton(
          onPressed: _isLoading ? null : _copyReportToClipboard,
          tooltip: 'Copy Report',
          heroTag: 'copyFab',
          backgroundColor: Colors.blue,
          child: const Icon(Icons.copy),
        ),
        const SizedBox(height: 10),
        FloatingActionButton(
          onPressed: _isLoading ? null : _deleteProductionLogs,
          tooltip: 'Delete Logs in Range',
          heroTag: 'deleteFab',
          backgroundColor: Theme.of(context).colorScheme.error,
          child: const Icon(Icons.delete_forever),
        ),
      ],
    );
  }
}

// --- Inventory Reporter Screen ---
class InventoryReporterScreen extends StatefulWidget {
  const InventoryReporterScreen({super.key});

  @override
  State<InventoryReporterScreen> createState() => _InventoryReporterScreenState();
}

class _InventoryReporterScreenState extends State<InventoryReporterScreen> {
  String _inventoryReport = 'Loading inventory report...'; // Text summary of inventory
  bool _isLoading = false; // Loading state

  @override
  void initState() {
    super.initState();
    _fetchInventoryReport(); // Fetch report on init
  }

  // Fetches the inventory report from the backend
  Future<void> _fetchInventoryReport() async {
    setState(() {
      _isLoading = true;
      _inventoryReport = 'Fetching latest inventory data...';
    });
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/items/inventory-report/'));
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _inventoryReport = data['report'] ?? 'No inventory report available.'; // Set report text
        });
      } else {
        setState(() {
          _inventoryReport = 'Error fetching inventory report: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _inventoryReport = 'Network error fetching inventory report: $e';
      });
    } finally {
      setState(() {
        _isLoading = false; // End loading
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Current Inventory Summary',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
          ),
          const SizedBox(height: 16),
          _isLoading
              ? const Center(child: CircularProgressIndicator()) // Show loading
              : Expanded(
                  child: SingleChildScrollView(
                    child: Card(
                      elevation: 2,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Text(
                          _inventoryReport,
                          style: GoogleFonts.inter(fontSize: 16, color: Colors.black87),
                        ),
                      ),
                    ),
                  ),
                ),
          const SizedBox(height: 16),
          Center(
            child: ElevatedButton.icon( // Refresh button
              onPressed: _isLoading ? null : _fetchInventoryReport,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh Report'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.secondary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// --- FULLY IMPLEMENTED STAFF MANAGEMENT SCREEN ---
class StaffManagementScreen extends StatefulWidget {
  const StaffManagementScreen({super.key});
  @override
  _StaffManagementScreenState createState() => _StaffManagementScreenState();
}

class _StaffManagementScreenState extends State<StaffManagementScreen> {
  List<dynamic> _allStaff = []; // All staff members fetched
  List<dynamic> _filteredStaff = []; // Staff members filtered by search
  bool _isLoading = true; // Loading state
  String _error = ''; // Error message
  final TextEditingController _searchController = TextEditingController(); // Search input controller

  @override
  void initState() {
    super.initState();
    _fetchStaff(); // Fetch staff on init
    _searchController.addListener(_filterStaff); // Listen for search input changes
  }
  
  @override
  void dispose() {
    _searchController.removeListener(_filterStaff);
    _searchController.dispose();
    super.dispose();
  }

  // Fetches all staff members from the backend
  Future<void> _fetchStaff() async {
    setState(() { _isLoading = true; _error = ''; }); // Set loading state
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/staff/list/'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            _allStaff = jsonDecode(utf8.decode(response.bodyBytes)); // Parse all staff
            _filteredStaff = _allStaff; // Initialize filtered list with all staff
            _isLoading = false; // End loading
          });
        }
      } else {
        throw Exception('Failed to load staff'); // Throw error
      }
    } catch (e) {
      if (mounted) {
        setState(() { _error = 'Failed to load staff: $e'; _isLoading = false; }); // Set error state
      }
    }
  }

  // Filters staff members based on search query
  void _filterStaff() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredStaff = _allStaff.where((staff) {
        final staffName = (staff['name'] as String?)?.toLowerCase() ?? '';
        return staffName.contains(query);
      }).toList();
    });
  }

  // Deletes a staff member by ID
  void _deleteStaff(String staffId, String staffName) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete staff member "$staffName"?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Delete', style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm != true) return; // If user cancels, do nothing

    try {
      final response = await http.delete(Uri.parse('$API_BASE_URL/staff/delete/$staffId/')); // Send DELETE request
      if (response.statusCode == 204) { // 204 No Content indicates successful deletion
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Staff deleted successfully'), backgroundColor: Colors.green));
        _fetchStaff(); // Refresh the list after deletion
      } else {
        throw Exception('Failed to delete staff. Server responded with status ${response.statusCode}');
      }
    } catch(e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error deleting staff: $e'), backgroundColor: Colors.red));
    }
  }

  // Shows the staff dialog for adding or editing a staff member
  void _showStaffDialog({Map<String, dynamic>? staff}) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _StaffDialog(staff: staff, onSave: _fetchStaff), // Pass staff for editing, onSave to refresh list
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator( // Pull to refresh functionality
        onRefresh: _fetchStaff,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: TextField( // Search input field
                controller: _searchController,
                decoration: InputDecoration(
                  labelText: 'Search Staff',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(icon: const Icon(Icons.clear), onPressed: () => _searchController.clear())
                      : null,
                ),
              ),
            ),
            if (_isLoading)
              const Expanded(child: Center(child: CircularProgressIndicator()))
            else if (_error.isNotEmpty)
              Expanded(child: Center(child: Text(_error)))
            else if (_filteredStaff.isEmpty)
              const Expanded(child: Center(child: Text('No staff members found.')))
            else
              Expanded(
                child: ListView.builder( // Display staff members in a list
                  padding: const EdgeInsets.only(bottom: 80),
                  itemCount: _filteredStaff.length,
                  itemBuilder: (context, index) {
                    final staff = _filteredStaff[index];
                    final imageUrl = (staff['image_urls'] as List?)?.isNotEmpty ?? false ? staff['image_urls'][0] : null;
                    final salary = (staff['salary'] as num?)?.toDouble() ?? 0.0;

                    return Card(
                      child: ListTile(
                        isThreeLine: true,
                        leading: CircleAvatar( // Staff image or placeholder
                          backgroundImage: imageUrl != null ? NetworkImage(imageUrl) : null,
                          child: imageUrl == null ? Text(staff['name']?[0] ?? 'S') : null,
                        ),
                        title: Text(staff['name'] ?? 'No Name', style: const TextStyle(fontWeight: FontWeight.bold)),
                        // --- MODIFIED ---: Changed to show salary per day
                        subtitle: Text(
                          '${staff['role'] ?? 'No Role'}\nSalary: ₹${salary.toStringAsFixed(2)} / day'
                        ),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(icon: const Icon(Icons.edit, color: Colors.blue), onPressed: () => _showStaffDialog(staff: staff)), // Edit button
                            IconButton(icon: const Icon(Icons.delete, color: Colors.red), onPressed: () => _deleteStaff(staff['id'], staff['name'])), // Delete button
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton( // Button to add new staff
        onPressed: () => _showStaffDialog(),
        tooltip: 'Add Staff',
        child: const Icon(Icons.add),
      ),
    );
  }
}

// --- Dialog for Adding/Editing Staff ---
class _StaffDialog extends StatefulWidget {
  final Map<String, dynamic>? staff;
  final VoidCallback onSave;
  const _StaffDialog({this.staff, required this.onSave});

  @override
  _StaffDialogState createState() => _StaffDialogState();
}

class _StaffDialogState extends State<_StaffDialog> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController, _roleController, _contactController, _salaryController;
  XFile? _imageFile;
  final ImagePicker _picker = ImagePicker();
  bool _isSaving = false;
  bool get _isEditing => widget.staff != null;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.staff?['name'] ?? '');
    _roleController = TextEditingController(text: widget.staff?['role'] ?? '');
    _contactController = TextEditingController(text: widget.staff?['contact_number'] ?? '');
    _salaryController = TextEditingController(text: widget.staff?['salary']?.toString() ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _roleController.dispose();
    _contactController.dispose();
    _salaryController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final pickedFile = await _picker.pickImage(source: source, imageQuality: 50);
      if(pickedFile != null) setState(() => _imageFile = pickedFile);
    } catch (e) {
      print("Image picker error: $e");
    }
  }

  Future<String?> _uploadImage(XFile imageFile) async {
    final uploadUrl = Uri.parse('$API_BASE_URL/staff/upload-image/');
    var request = http.MultipartRequest('POST', uploadUrl);
    request.files.add(await http.MultipartFile.fromPath('file', imageFile.path, contentType: MediaType('image', 'jpeg'))); 
    try {
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      if(response.statusCode == 201) return jsonDecode(response.body)['image_url'];
    } catch (e) {
      print("Image upload failed: $e");
    }
    return null;
  }

  Future<void> _saveStaff() async {
    if (!_formKey.currentState!.validate() || _isSaving) return;
    setState(() => _isSaving = true);
    
    List<String> imageUrls = (widget.staff?['image_urls'] as List?)?.map((e) => e.toString()).toList() ?? [];
    if (_imageFile != null) {
        String? newUrl = await _uploadImage(_imageFile!);
        if (newUrl != null) {
            imageUrls = [newUrl];
        } else {
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Image upload failed!'), backgroundColor: Colors.red));
            setState(() => _isSaving = false);
            return;
        }
    }

    final staffData = {
      'name': _nameController.text,
      'role': _roleController.text,
      'contact_number': _contactController.text,
      'salary': double.tryParse(_salaryController.text) ?? 0.0,
      'image_urls': imageUrls,
    };
    
    final url = _isEditing
        ? '$API_BASE_URL/staff/edit/${widget.staff!['id']}/'  
        : '$API_BASE_URL/staff/add/';
    
    final request = http.Request(_isEditing ? 'PUT' : 'POST', Uri.parse(url))
      ..headers['Content-Type'] = 'application/json'
      ..body = jsonEncode(staffData);

    try {
        final streamedResponse = await request.send();
        final response = await http.Response.fromStream(streamedResponse);
        if (mounted) {
            if (response.statusCode == 200 || response.statusCode == 201) {
                widget.onSave();
                Navigator.of(context).pop();
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Staff member saved!'), backgroundColor: Colors.green));
            } else {
                final errorData = jsonDecode(response.body);
                final errorMessage = errorData['error'] ?? 'An unknown error occurred';
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $errorMessage'), backgroundColor: Colors.red));
            }
        }
    } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Network Error: $e'), backgroundColor: Colors.red));
    } finally {
        if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEditing ? 'Edit Staff' : 'Add Staff'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(controller: _nameController, decoration: const InputDecoration(labelText: 'Name'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _roleController, decoration: const InputDecoration(labelText: 'Role'), validator: (v) => v!.isEmpty ? 'Required' : null),
              TextFormField(controller: _contactController, decoration: const InputDecoration(labelText: 'Contact'), keyboardType: TextInputType.phone, validator: (v) => v!.isEmpty ? 'Required' : null),
              // --- MODIFIED ---: Changed label for clarity
              TextFormField(controller: _salaryController, decoration: const InputDecoration(labelText: 'Salary (Per Day)'), keyboardType: TextInputType.number, validator: (v) => v!.isEmpty ? 'Required' : null),
              const SizedBox(height: 16),
              Container(
                height: 120, width: 120,
                decoration: BoxDecoration(
                  color: Colors.grey[200],
                  shape: BoxShape.circle,
                  image: _imageFile != null
                      ? DecorationImage(image: (kIsWeb ? NetworkImage(_imageFile!.path) : FileImage(File(_imageFile!.path))) as ImageProvider, fit: BoxFit.cover)
                      : (((widget.staff?['image_urls'] as List?) ?? []).isNotEmpty
                          ? DecorationImage(image: NetworkImage(widget.staff!['image_urls'][0]), fit: BoxFit.cover)
                          : null),
                ),
                child: (_imageFile == null && ((widget.staff?['image_urls'] as List?) ?? []).isEmpty) ? const Icon(Icons.person, size: 60, color: Colors.grey) : null,
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  TextButton.icon(onPressed: () => _pickImage(ImageSource.camera), icon: const Icon(Icons.camera_alt), label: const Text("Camera")),
                  TextButton.icon(onPressed: () => _pickImage(ImageSource.gallery), icon: const Icon(Icons.photo_library), label: const Text("Gallery")),
                ],
              )
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
        ElevatedButton(onPressed: _isSaving ? null : _saveStaff, child: _isSaving ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Save')),
      ],
    );
  }
}



// ===================================================================
// StaffAttendanceReportScreen - Manages staff attendance and salary payments
class StaffAttendanceReportScreen extends StatefulWidget {
  const StaffAttendanceReportScreen({super.key});
  @override
  State<StaffAttendanceReportScreen> createState() => _StaffAttendanceReportScreenState();
}

class _StaffAttendanceReportScreenState extends State<StaffAttendanceReportScreen> {
  List<dynamic> _salaryData = []; 
  bool _isLoading = true;
  DateTime? _startDate, _endDate;
  
  List<dynamic> _allStaffList = [];
  List<dynamic> _filteredStaffList = [];
  String? _selectedStaffId;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _startDate = DateTime.now().subtract(const Duration(days: 30));
    _endDate = DateTime.now();
    _fetchStaffListForFilter();
    _searchController.addListener(_filterStaffForReport);
  }

  @override
  void dispose() {
    _searchController.removeListener(_filterStaffForReport);
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _fetchStaffListForFilter() async {
    setState(() { _isLoading = true; });
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/staff/list/'));
      if (mounted && response.statusCode == 200) {
        setState(() {
          _allStaffList = jsonDecode(utf8.decode(response.bodyBytes));
          _allStaffList.insert(0, {'id': 'All Staff', 'name': 'All Staff'});
          _filteredStaffList = _allStaffList;
          _selectedStaffId = _allStaffList[0]['id'];
        });
        await _fetchAttendanceReport();
      }
    } catch (e) {
      if(mounted) _showSnackBar('Error loading staff list: $e', isError: true);
    } finally {
      if(mounted) setState(() { _isLoading = false; });
    }
  }

  void _filterStaffForReport() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredStaffList = [
        _allStaffList.first,
        ..._allStaffList.where((staff) => staff['id'] != 'All Staff' && ((staff['name'] as String?)?.toLowerCase().contains(query) ?? false))
      ];
      if (_selectedStaffId != null && !_filteredStaffList.any((s) => s['id'] == _selectedStaffId)) {
        _selectedStaffId = _filteredStaffList[0]['id'];
        _fetchAttendanceReport();
      }
    });
  }

  Future<void> _selectDateRange(BuildContext context) async {
    final picked = await showDateRangePicker(context: context, initialDateRange: DateTimeRange(start: _startDate!, end: _endDate!), firstDate: DateTime(2023), lastDate: DateTime.now().add(const Duration(days: 365)));
    if (picked != null) {
      setState(() { _startDate = picked.start; _endDate = picked.end; });
      _fetchAttendanceReport();
    }
  }

  Future<void> _fetchAttendanceReport() async {
    setState(() { _isLoading = true; });
    try {
      Map<String, String> queryParams = {
        'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
        'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
      };
      if (_selectedStaffId != null && _selectedStaffId != 'All Staff') {
        queryParams['staff_id'] = _selectedStaffId!;
      }
      
      final uri = Uri.parse('$API_BASE_URL/staff/attendance-report/').replace(queryParameters: queryParams);
      final response = await http.get(uri);

      if (mounted) {
        if (response.statusCode == 200) {
          final data = jsonDecode(utf8.decode(response.bodyBytes));
          setState(() { 
            _salaryData = data is List ? data : []; 
          });
        } else {
          throw Exception('Failed to fetch report: ${response.statusCode}');
        }
      }
    } catch (e) {
      if (mounted) _showSnackBar('Error fetching report: $e', isError: true);
    } finally {
      if (mounted) setState(() { _isLoading = false; });
    }
  }

  Future<void> _showPaySalaryDialog(String staffId, String staffName, double calculatedAmount) async {
    final amountController = TextEditingController(text: calculatedAmount.toStringAsFixed(2));
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Pay Salary for $staffName'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Calculated salary for this period is ₹${calculatedAmount.toStringAsFixed(2)}. You can adjust the final amount below.'),
            const SizedBox(height: 16),
            TextField(
              controller: amountController,
              decoration: const InputDecoration(
                labelText: 'Final Payout Amount',
                prefixText: '₹',
                border: OutlineInputBorder(),
              ),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Confirm Payment')),
        ],
      ),
    );

    if (confirm == true) {
      final finalAmount = double.tryParse(amountController.text) ?? calculatedAmount;
      _updateSalaryStatus(staffId, staffName, finalAmount, true);
    }
  }

  Future<void> _updateSalaryStatus(String staffId, String staffName, double amount, bool newStatus) async {
    if (!newStatus) {
      final confirmUnpay = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Confirm Reversal'),
          content: const Text('Are you sure you want to mark this salary as UNPAID? This will delete the associated expense record.'),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Confirm', style: TextStyle(color: Colors.orange))),
          ],
        ),
      );
      if (confirmUnpay != true) return;
    }

    setState(() => _isLoading = true);
    try {
      final uri = Uri.parse('$API_BASE_URL/staff/salary/mark-paid/');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'staff_id': staffId,
          'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
          'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
          'amount': amount,
          'status': newStatus,
        }),
      );
      if (mounted) {
        if (response.statusCode == 200) {
          _showSnackBar('Salary for $staffName has been updated.');
          await _fetchAttendanceReport();
        } else {
          final error = jsonDecode(response.body)['error'] ?? 'Failed to update status';
          throw Exception(error);
        }
      }
    } catch (e) {
      if(mounted) _showSnackBar('Error: $e', isError: true);
    } finally {
      if(mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _deleteAttendanceLogs() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete attendance records from ${DateFormat.yMMMd().format(_startDate!)} to ${DateFormat.yMMMd().format(_endDate!)}? This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('DELETE', style: TextStyle(color: Colors.red))),
        ],
      ),
    );

    if (confirm != true) return;
    setState(() => _isLoading = true);

    try {
      final queryParams = {
          'start_date': DateFormat('yyyy-MM-dd').format(_startDate!),
          'end_date': DateFormat('yyyy-MM-dd').format(_endDate!),
        };
      if (_selectedStaffId != null && _selectedStaffId != 'All Staff') {
        queryParams['staff_id'] = _selectedStaffId!;
      }

      final uri = Uri.parse('$API_BASE_URL/staff/attendance/delete-range/').replace(queryParameters: queryParams);
      final response = await http.delete(uri);

      if(mounted) {
        if (response.statusCode == 200) {
          final data = jsonDecode(utf8.decode(response.bodyBytes));
          _showSnackBar(data['message'] ?? 'Records deleted.');
          _fetchAttendanceReport();
        } else {
          throw Exception('Failed to delete: ${response.body}');
        }
      }
    } catch (e) {
      if(mounted) _showSnackBar('Error: $e', isError: true);
    } finally {
      if(mounted) setState(() => _isLoading = false);
    }
  }
  
  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? Colors.red.shade700 : Colors.green.shade700,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Staff Salary Management', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary)),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () => _selectDateRange(context),
              icon: const Icon(Icons.calendar_today),
              label: Text('${DateFormat.yMMMd().format(_startDate!)} - ${DateFormat.yMMMd().format(_endDate!)}'),
              style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: TextField(controller: _searchController, decoration: const InputDecoration(labelText: 'Search Staff...', prefixIcon: Icon(Icons.search)))),
                const SizedBox(width: 16),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _selectedStaffId,
                    decoration: const InputDecoration(labelText: 'Filter by Staff', border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 10)),
                    items: _filteredStaffList.map<DropdownMenuItem<String>>((staff) => DropdownMenuItem<String>(value: staff['id'], child: Text(staff['name'], overflow: TextOverflow.ellipsis))).toList(),
                    onChanged: _isLoading ? null : (value) { setState(() => _selectedStaffId = value); _fetchAttendanceReport(); },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _isLoading
                ? const Expanded(child: Center(child: CircularProgressIndicator()))
                : Expanded(
                    child: _salaryData.isEmpty
                        ? const Center(child: Text('No salary data available for the selected period.'))
                        : ListView.builder(
                            itemCount: _salaryData.length,
                            itemBuilder: (context, index) {
                              final staffReport = _salaryData[index];
                              final staffId = staffReport['staff_id'];
                              final staffName = staffReport['staff_name'] ?? 'Unknown';
                              final salaryDue = (staffReport['total_salary_due'] as num?)?.toDouble() ?? 0.0;
                              final isPaid = staffReport['is_paid'] as bool? ?? false;
                              final hoursWorked = (staffReport['total_hours_worked'] as num?)?.toDouble() ?? 0.0;

                              return Card(
                                margin: const EdgeInsets.only(bottom: 12.0),
                                elevation: isPaid ? 1 : 4,
                                color: isPaid ? Colors.green.shade50 : Colors.white,
                                child: Padding(
                                  padding: const EdgeInsets.all(16.0),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(staffName, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                                            const SizedBox(height: 8),
                                            Text('Salary Due: ₹${salaryDue.toStringAsFixed(2)}', style: Theme.of(context).textTheme.titleMedium),
                                            // --- MODIFIED: Display total hours ---
                                            Text('Total Hours: ${hoursWorked.toStringAsFixed(1)} hrs', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey.shade700)),
                                            Text('Present: ${staffReport['total_days_present']} days', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey.shade700)),
                                          ],
                                        ),
                                      ),
                                      isPaid
                                          ? Column(
                                              crossAxisAlignment: CrossAxisAlignment.end,
                                              children: [
                                                const Chip(label: Text('PAID'), backgroundColor: Colors.green, labelStyle: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                                                TextButton(onPressed: () => _updateSalaryStatus(staffId, staffName, salaryDue, false), child: Text('Mark as Unpaid', style: TextStyle(color: Colors.orange.shade800))),
                                              ],
                                            )
                                          : ElevatedButton.icon(
                                              onPressed: () => _showPaySalaryDialog(staffId, staffName, salaryDue),
                                              icon: const Icon(Icons.payment),
                                              label: const Text('Pay Salary'),
                                              style: ElevatedButton.styleFrom(
                                                backgroundColor: Theme.of(context).colorScheme.primary,
                                                foregroundColor: Colors.white
                                              ),
                                            ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                  ),
          ],
        ),
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          FloatingActionButton(
            onPressed: _isLoading ? null : _fetchAttendanceReport,
            tooltip: 'Refresh',
            heroTag: 'refresh_attendance',
            child: const Icon(Icons.refresh),
          ),
          const SizedBox(height: 10),
          FloatingActionButton(
            onPressed: _isLoading ? null : _deleteAttendanceLogs,
            tooltip: 'Delete Logs in Range',
            heroTag: 'delete_attendance',
            backgroundColor: Theme.of(context).colorScheme.error,
            child: const Icon(Icons.delete_forever),
          ),
        ],
      )
    );
  }
}




// --- CCTVReportScreen Widget - Displays CCTV observation reports ---
class CCTVReportScreen extends StatefulWidget {
  const CCTVReportScreen({super.key});

  @override
  State<CCTVReportScreen> createState() => _CCTVReportScreenState();
}

class _CCTVReportScreenState extends State<CCTVReportScreen> {
  String _cctvReport = 'Loading CCTV report...'; // Text summary of CCTV observations
  bool _isLoading = false; // Loading state
  DateTime? _startDate; // Start date for report
  DateTime? _endDate; // End date for report
  String? _selectedStaffId; // Filter by staff
  // UPDATED LOCATIONS LIST for Asthana Bakery (for filter)
  final List<String> _locations = ['All Locations', 'vailathur_main_bakery', 'vailathur_cafe', 'vellachal_outlet', 'vellachal_production'];
  String? _selectedLocationId; // Filter by location (camera_id is more specific)

  List<dynamic> _staffList = []; // For staff filter dropdown

  @override
  void initState() {
    super.initState();
    // Default date range: last 7 days
    _startDate = DateTime.now().subtract(const Duration(days: 6)); 
    _endDate = DateTime.now();
    _selectedLocationId = _locations[0]; // Default to All Locations
    _fetchStaffListForFilter().then((_) { // Fetch staff list then CCTV report
      _fetchCCTVReport();
    });
  }

  // Fetches the list of staff members for the filter dropdown
  Future<void> _fetchStaffListForFilter() async {
    final listStaffUrl = Uri.parse('$API_BASE_URL/staff/list/');    
    try {
      final response = await http.get(listStaffUrl);
      if (response.statusCode == 200) {
        setState(() {
          _staffList = jsonDecode(utf8.decode(response.bodyBytes));
          _staffList.insert(0, {'id': 'All Staff', 'name': 'All Staff'}); // Add "All Staff" option
          _selectedStaffId = _staffList[0]['id']; // Select "All Staff" by default
        });
      } else {
        _showSnackBar('Failed to load staff list for CCTV filter: ${response.statusCode}');
      }
    } catch (e) {
      _showSnackBar('Error loading staff list for CCTV filter: $e');
    }
  }

  // Shows a date range picker
  Future<void> _selectDateRange(BuildContext context) async {
    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2023, 1),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDateRange: DateTimeRange(start: _startDate ?? DateTime.now(), end: _endDate ?? DateTime.now()),
      builder: (BuildContext context, Widget? child) {
        return Theme(
          data: ThemeData.light().copyWith(
            primaryColor: Theme.of(context).colorScheme.primary,
            colorScheme: ColorScheme.light(primary: Theme.of(context).colorScheme.primary),
            buttonTheme: const ButtonThemeData(textTheme: ButtonTextTheme.primary),
          ),
          child: child!,
        );
      },
    );
    if (picked != null && (picked.start != _startDate || picked.end != _endDate)) {
      setState(() {
        _startDate = picked.start;
        _endDate = picked.end;
      });
      _fetchCCTVReport(); // Fetch report with new dates
    }
  }

  // Fetches the CCTV observation report from the backend
  Future<void> _fetchCCTVReport() async {
    setState(() {
      _isLoading = true;
      _cctvReport = 'Fetching latest CCTV observation data...';
    });
    try {
      Map<String, String> queryParams = {};
      if (_startDate != null) {
        queryParams['start_date'] = DateFormat('yyyy-MM-dd').format(_startDate!);
      }
      if (_endDate != null) {
        queryParams['end_date'] = DateFormat('yyyy-MM-dd').format(_endDate!);
      }
      if (_selectedStaffId != null && _selectedStaffId != 'All Staff') {
        queryParams['staff_id'] = _selectedStaffId!; // Add staff filter
      }
      if (_selectedLocationId != null && _selectedLocationId != 'All Locations') {
        queryParams['location_id'] = _selectedLocationId!; // Add location filter
      }

      final uri = Uri.parse('$API_BASE_URL/staff/cctv-observation-report/').replace(queryParameters: queryParams);
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _cctvReport = data['report'] ?? 'No CCTV observations found for the selected criteria.'; // Set report text
        });
      } else {
        _showSnackBar('Error fetching CCTV report: ${response.statusCode} ${response.body}');
        setState(() {
          _cctvReport = 'Error fetching CCTV report: ${response.statusCode}';
        });
      }
    } catch (e) {
      _showSnackBar('Network error fetching CCTV report: $e');
      setState(() {
        _cctvReport = 'Network error fetching CCTV report: $e';
      });
    } finally {
      setState(() {
        _isLoading = false; // End loading
      });
    }
  }

  // Shows a SnackBar message
  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'CCTV Observation Report',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
          ),
          const SizedBox(height: 16),
          // Filters row
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon( // Date range picker button
                  onPressed: () => _selectDateRange(context),
                  icon: const Icon(Icons.calendar_today),
                  label: Text(_startDate == null || _endDate == null
                      ? 'Select Date Range'
                      : '${DateFormat('MMM d,yyyy').format(_startDate!)} - ${DateFormat('MMM d,yyyy').format(_endDate!)}'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.secondary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              if (_staffList.isNotEmpty) // Staff filter dropdown
                DropdownButton<String>(
                  value: _selectedStaffId,
                  items: _staffList.map<DropdownMenuItem<String>>((staff) {
                    return DropdownMenuItem<String>(
                      value: staff['id'],
                      child: Text(staff['name'] ?? 'Unknown Staff'),
                    );
                  }).toList(),
                  onChanged: (String? newValue) {
                    setState(() {
                      _selectedStaffId = newValue;
                    });
                    _fetchCCTVReport(); // Fetch report with new staff filter
                  },
                  style: GoogleFonts.inter(color: Colors.black87),
                  icon: const Icon(Icons.arrow_drop_down),
                  underline: Container(height: 2, color: Theme.of(context).colorScheme.primary),
                ),
              const SizedBox(width: 8),
              DropdownButton<String>( // Location filter dropdown
                value: _selectedLocationId,
                items: _locations.map((String location) {
                  return DropdownMenuItem<String>(
                    value: location,
                    child: Text(_toTitleCase(location.replaceAll('_', ' '))),
                  );
                }).toList(),
                onChanged: (String? newValue) {
                  setState(() {
                    _selectedLocationId = newValue;
                  });
                  _fetchCCTVReport(); // Fetch report with new location filter
                },
                style: GoogleFonts.inter(color: Colors.black87),
                icon: const Icon(Icons.arrow_drop_down),
                underline: Container(height: 2, color: Theme.of(context).colorScheme.primary),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _isLoading
              ? const Center(child: CircularProgressIndicator()) // Show loading
              : Expanded(
                  child: SingleChildScrollView(
                    child: Card(
                      elevation: 2,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Text(
                          _cctvReport,
                          style: GoogleFonts.inter(fontSize: 16, color: Colors.black87),
                        ),
                      ),
                    ),
                  ),
                ),
          const SizedBox(height: 16),
          Center(
            child: ElevatedButton.icon( // Refresh button
              onPressed: _isLoading ? null : _fetchCCTVReport,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh Report'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.secondary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// --- NEW: CustomerReportScreen Widget ---
class CustomerReportScreen extends StatefulWidget {
  const CustomerReportScreen({super.key});

  @override
  State<CustomerReportScreen> createState() => _CustomerReportScreenState();
}

class _CustomerReportScreenState extends State<CustomerReportScreen> {
  String _customerReport = 'Loading customer report...'; // Text summary of customer report
  bool _isLoading = false; // Loading state
  DateTime? _startDate; // Start date for report
  DateTime? _endDate; // End date for report
  // UPDATED OUTLETS LIST for Asthana Bakery (for sales reports)
  final List<String> _outlets = ['All Outlets', 'vailathur_main_bakery', 'vailathur_cafe', 'vellachal_outlet'];
  String? _selectedOutlet; // Filter by outlet

  @override
  void initState() {
    super.initState();
    // Default date range: last 30 days
    _startDate = DateTime.now().subtract(const Duration(days: 30)); 
    _endDate = DateTime.now();
    _selectedOutlet = _outlets[0]; // Default to All Outlets
    _fetchCustomerReport(); // Fetch report on init
  }

  // Shows a date range picker
  Future<void> _selectDateRange(BuildContext context) async {
    final DateTimeRange? picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2023, 1),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDateRange: DateTimeRange(start: _startDate ?? DateTime.now(), end: _endDate ?? DateTime.now()),
      builder: (BuildContext context, Widget? child) {
        return Theme(
          data: ThemeData.light().copyWith(
            primaryColor: Theme.of(context).colorScheme.primary,
            colorScheme: ColorScheme.light(primary: Theme.of(context).colorScheme.primary),
            buttonTheme: const ButtonThemeData(textTheme: ButtonTextTheme.primary),
          ),
          child: child!,
        );
      },
    );
    if (picked != null && (picked.start != _startDate || picked.end != _endDate)) {
      setState(() {
        _startDate = picked.start;
        _endDate = picked.end;
      });
      _fetchCustomerReport(); // Fetch report with new dates
    }
  }

  // Fetches the customer report from the backend
  Future<void> _fetchCustomerReport() async {
    setState(() {
      _isLoading = true;
      _customerReport = 'Fetching latest customer data...';
    });
    try {
      Map<String, String> queryParams = {};
      if (_startDate != null) {
        queryParams['start_date'] = DateFormat('yyyy-MM-dd').format(_startDate!);
      }
      if (_endDate != null) {
        queryParams['end_date'] = DateFormat('yyyy-MM-dd').format(_endDate!);
      }
      if (_selectedOutlet != null && _selectedOutlet != 'All Outlets') {
        queryParams['outlet_id'] = _selectedOutlet!; // Filter by outlet
      }

      // This endpoint is from sales/views.py
      final uri = Uri.parse('$API_BASE_URL/sales/customer-transactions-report/').replace(queryParameters: queryParams);
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _customerReport = data['report'] ?? 'No customer report available for the selected criteria.'; // Set report text
        });
      } else {
        _showSnackBar('Error fetching customer report: ${response.statusCode} ${response.body}');
        setState(() {
          _customerReport = 'Error fetching customer report: ${response.statusCode}';
        });
      }
    } catch (e) {
      _showSnackBar('Network error fetching customer report: $e');
      setState(() {
        _customerReport = 'Network error fetching customer report: $e';
      });
    } finally {
      setState(() {
        _isLoading = false; // End loading
      });
    }
  }

  // Shows a SnackBar message
  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Customer Report',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
          ),
          const SizedBox(height: 16),
          // Filters row
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon( // Date range picker button
                  onPressed: () => _selectDateRange(context),
                  icon: const Icon(Icons.calendar_today),
                  label: Text(_startDate == null || _endDate == null
                      ? 'Select Date Range'
                      : '${DateFormat('MMM d,yyyy').format(_startDate!)} - ${DateFormat('MMM d,yyyy').format(_endDate!)}'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.secondary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              DropdownButton<String>( // Outlet filter dropdown
                value: _selectedOutlet,
                items: _outlets.map((String outlet) {
                  return DropdownMenuItem<String>(
                    value: outlet,
                    child: Text(_toTitleCase(outlet.replaceAll('_', ' '))),
                  );
                }).toList(),
                onChanged: (String? newValue) {
                  setState(() {
                    _selectedOutlet = newValue;
                  });
                  _fetchCustomerReport(); // Fetch report with new outlet filter
                },
                style: GoogleFonts.inter(color: Colors.black87),
                icon: const Icon(Icons.arrow_drop_down),
                underline: Container(height: 2, color: Theme.of(context).colorScheme.primary),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _isLoading
              ? const Center(child: CircularProgressIndicator()) // Show loading
              : Expanded(
                  child: SingleChildScrollView(
                    child: Card(
                      elevation: 2,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Text(
                          _customerReport,
                          style: GoogleFonts.inter(fontSize: 16, color: Colors.black87),
                        ),
                      ),
                    ),
                  ),
                ),
          const SizedBox(height: 16),
          Center(
            child: ElevatedButton.icon( // Refresh button
              onPressed: _isLoading ? null : _fetchCustomerReport,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh Report'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.secondary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// --- About Screen - Displays app information and developer contact ---
class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  void _launchURL(String url) async {
    final uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      print('Could not launch $url');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100],
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildHeader(context),
          const SizedBox(height: 24),
          _buildInfoCard(context),
          const SizedBox(height: 24),
          _buildContactCard(context),
          const SizedBox(height: 48),
          _buildFooter(context),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Center(
      child: Column(
        children: [
          CircleAvatar(
            radius: 50,
            backgroundColor: Theme.of(context).colorScheme.primary.withOpacity(0.1),
            child: Icon(
              Icons.storefront,
              size: 50,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Barghah',
            style: GoogleFonts.poppins(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Advanced Bakery Management Solutions',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey.shade700,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoCard(BuildContext context) {
    return Card(
      elevation: 4.0,
      shadowColor: Colors.black.withOpacity(0.1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "About This App",
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Text(
              'This application is a comprehensive POS, production, and inventory management system designed specifically for Asthana Bakery. It streamlines daily operations from sales to production, ensuring efficiency and accuracy.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.grey.shade800, height: 1.5),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContactCard(BuildContext context) {
    return Card(
      elevation: 4.0,
      shadowColor: Colors.black.withOpacity(0.1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12.0),
        child: Column(
          children: [
            _buildContactTile(
              context,
              icon: Icons.person_outline,
              title: 'Lead Developer',
              subtitle: 'Sabith',
            ),
            const Divider(indent: 20, endIndent: 20),
            _buildContactTile(
              context,
              icon: Icons.phone_outlined,
              title: 'Business Inquiries',
              subtitle: '+91 79942 35150',
              onTap: () => _launchURL('tel:+917994235150'),
            ),
            const Divider(indent: 20, endIndent: 20),
             _buildContactTile(
              context,
              icon: Icons.chat_bubble_outline,
              title: 'WhatsApp Support',
              subtitle: 'Chat with us',
              onTap: () => _launchURL('https://wa.me/917994235150'),
            ),
             const Divider(indent: 20, endIndent: 20),
             _buildContactTile(
              context,
              icon: Icons.camera_alt_outlined,
              title: 'Follow us on Instagram',
              subtitle: '@barghah_solutions',
              onTap: () => _launchURL('https://www.instagram.com/barghah_solutions'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContactTile(BuildContext context, {required IconData icon, required String title, required String subtitle, VoidCallback? onTap}) {
    return ListTile(
      leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(subtitle, style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.grey.shade700)),
      onTap: onTap,
      trailing: onTap != null ? const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey) : null,
    );
  }

  Widget _buildFooter(BuildContext context) {
    return Text(
      '© 2025 Barghah. All rights reserved.',
      textAlign: TextAlign.center,
      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
    );
  }
}