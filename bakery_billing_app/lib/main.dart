import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:google_fonts/google_fonts.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:intl/intl.dart' as intl;
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';

// --- CORRECTED & VERIFIED IMPORTS ---
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
// --- CORRECTED IMPORTS WITH PREFIXES ---
import 'package:flutter_esc_pos_utils/flutter_esc_pos_utils.dart';
import 'package:flutter_esc_pos_network/flutter_esc_pos_network.dart' as network;
import 'package:blue_thermal_printer/blue_thermal_printer.dart';
import 'dart:typed_data';

// --- CONFIGURATION ---
const String API_BASE_URL = 'https://bakery-backend-5qkn.onrender.com'; // USE YOUR SERVER IP

void main() {
  runApp(const BillingApp());
}

class BillingApp extends StatelessWidget {
  const BillingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Asthana Bakery POS',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6A0B0B),
          primary: const Color(0xFF6A0B0B),
          secondary: Colors.amber.shade700,
        ),
        scaffoldBackgroundColor: const Color(0xFFFFF8F1),
        textTheme: GoogleFonts.interTextTheme(Theme.of(context).textTheme),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF6A0B0B),
          foregroundColor: Colors.white,
          elevation: 2,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF6A0B0B),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          ),
        ),
      ),
      home: const BillingScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

// --- DATA MODELS ---
class Outlet {
  final String id;
  final String name;
  final String? phone;
  final String type;

  Outlet({required this.id, required this.name, this.phone, this.type = 'sales'});

  factory Outlet.fromJson(Map<String, dynamic> json) {
    return Outlet(
      id: json['id'] ?? '',
      name: json['name'] ?? 'Unknown',
      phone: json['phone'],
      type: json['type'] ?? 'sales',
    );
  }
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Outlet && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}

class Staff {
  final String id;
  final String name;

  Staff({required this.id, required this.name});

  factory Staff.fromJson(Map<String, dynamic> json) {
    return Staff(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? 'Unknown Staff',
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Staff && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}

class Product {
  final String id;
  final String name;
  final double price;
  final String unitType;
  final String img;
  final String? barcode;
  final int stock;
  final int lowStockThreshold;

  Product({
    required this.id,
    required this.name,
    required this.price,
    this.unitType = 'piece',
    this.img = '',
    this.barcode,
    required this.stock,
    required this.lowStockThreshold,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] ?? '',
      name: json['name'] ?? 'Unknown',
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      unitType: json['unit_type'] ?? 'piece',
      img: json['image_url'] ?? '',
      barcode: json['barcode'],
      stock: (json['stock'] as num?)?.toInt() ?? 0,
      lowStockThreshold: (json['low_stock_threshold'] as num?)?.toInt() ?? 10,
    );
  }
}

class CartItem {
  final String cartId;
  final Product product;
  int quantity;
  double weightGrams;
  double customPrice;
  final bool isCustomPriceItem;

  CartItem({
    required this.cartId,
    required this.product,
    this.quantity = 0,
    this.weightGrams = 0.0,
    this.customPrice = 0.0,
    this.isCustomPriceItem = false,
  });

  bool get isByPiece => product.unitType == 'piece' && !isCustomPriceItem;
  bool get isByWeight => product.unitType == 'kg' && !isCustomPriceItem;
  bool get isByCustomPrice => isCustomPriceItem;

  double get total {
    if (isByCustomPrice) return customPrice;
    if (isByPiece) return product.price * quantity;
    if (isByWeight) return (product.price / 1000) * weightGrams;
    return 0.0;
  }

  String get subtitle {
    if (isByPiece) return 'Qty: $quantity';
    if (isByWeight) return '${weightGrams.toStringAsFixed(0)} gm';
    if (isByCustomPrice) return 'Custom Price';
    return '';
  }

  String get displayPrice {
    if (isByCustomPrice) return '₹${customPrice.toStringAsFixed(2)}';
    if (isByPiece) return '₹${product.price.toStringAsFixed(2)} x $quantity';
    if (isByWeight) return '₹${product.price.toStringAsFixed(2)}/kg';
    return '';
  }
}

// --- WIDGETS ---
class BarcodeScannerScreen extends StatefulWidget {
  const BarcodeScannerScreen({Key? key}) : super(key: key);
  @override
  State<BarcodeScannerScreen> createState() => _BarcodeScannerScreenState();
}
class _BarcodeScannerScreenState extends State<BarcodeScannerScreen> {
  final MobileScannerController cameraController = MobileScannerController();
  bool isScanned = false;
  @override
  void dispose() {
    cameraController.dispose();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Barcode'),
        actions: [
          IconButton(
            icon: const Icon(Icons.camera_alt_outlined),
            tooltip: 'Switch Camera',
            onPressed: () => cameraController.switchCamera(),
          ),
        ],
      ),
      body: Stack(
        children: [
          MobileScanner(
            controller: cameraController,
            onDetect: (capture) {
              if (!isScanned && capture.barcodes.isNotEmpty) {
                final String? code = capture.barcodes.first.rawValue;
                if (code != null && code.isNotEmpty) {
                  setState(() => isScanned = true);
                  HapticFeedback.vibrate();
                  Navigator.of(context).pop(code);
                }
              }
            },
          ),
          Container(
            decoration: ShapeDecoration(
              shape: ScannerOverlayShape(
                borderColor: Colors.amber,
                borderRadius: 12,
                borderLength: 30,
                borderWidth: 4,
                cutOutSize: MediaQuery.of(context).size.width * 0.8,
              ),
            ),
          ),
          const Positioned(
            bottom: 100, left: 0, right: 0,
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Position the barcode within the frame to scan',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ScannerOverlayShape extends ShapeBorder {
  final Color borderColor;
  final double borderWidth;
  final Color overlayColor;
  final double borderRadius;
  final double borderLength;
  final double cutOutSize;
  const ScannerOverlayShape({
    this.borderColor = Colors.red,
    this.borderWidth = 3.0,
    this.overlayColor = const Color.fromRGBO(0, 0, 0, 80),
    this.borderRadius = 0,
    this.borderLength = 40,
    this.cutOutSize = 250,
  });
  @override
  EdgeInsetsGeometry get dimensions => const EdgeInsets.all(0);
  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) {
    return Path()
      ..fillType = PathFillType.evenOdd
      ..addPath(getOuterPath(rect, textDirection: textDirection), Offset.zero);
  }
  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) {
    return Path.combine(
      PathOperation.difference,
      Path()..addRect(rect),
      Path()
        ..addRRect(RRect.fromRectAndRadius(
            Rect.fromCenter(center: rect.center, width: cutOutSize, height: cutOutSize),
            Radius.circular(borderRadius))),
    );
  }
  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {
      final backgroundPaint = Paint()
      ..color = overlayColor
      ..style = PaintingStyle.fill;
      final borderPaint = Paint()
      ..color = borderColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = borderWidth;
      final boxPath = Path.combine(
      PathOperation.difference,
      Path()..addRect(rect),
      Path()
        ..addRRect(RRect.fromRectAndRadius(
            Rect.fromCenter(center: rect.center, width: cutOutSize, height: cutOutSize),
            Radius.circular(borderRadius))),
    );
    canvas.drawPath(boxPath, backgroundPaint);
    final cutOutRect = Rect.fromCenter(center: rect.center, width: cutOutSize, height: cutOutSize);
    canvas.drawPath(
        Path()
          ..moveTo(cutOutRect.left, cutOutRect.top + borderLength)
          ..lineTo(cutOutRect.left, cutOutRect.top)
          ..lineTo(cutOutRect.left + borderLength, cutOutRect.top),
        borderPaint);
    canvas.drawPath(
        Path()
          ..moveTo(cutOutRect.right - borderLength, cutOutRect.top)
          ..lineTo(cutOutRect.right, cutOutRect.top)
          ..lineTo(cutOutRect.right, cutOutRect.top + borderLength),
        borderPaint);
    canvas.drawPath(
        Path()
          ..moveTo(cutOutRect.right, cutOutRect.bottom - borderLength)
          ..lineTo(cutOutRect.right, cutOutRect.bottom)
          ..lineTo(cutOutRect.right, cutOutRect.bottom - borderLength),
        borderPaint);
    canvas.drawPath(
        Path()
          ..moveTo(cutOutRect.left + borderLength, cutOutRect.bottom)
          ..lineTo(cutOutRect.left, cutOutRect.bottom)
          ..lineTo(cutOutRect.left, cutOutRect.bottom - borderLength),
        borderPaint);
  }
  @override
  ShapeBorder scale(double t) {
    return ScannerOverlayShape(
      borderColor: borderColor, borderWidth: borderWidth, overlayColor: overlayColor,
      borderRadius: borderRadius, borderLength: borderLength, cutOutSize: cutOutSize,
    );
  }
}

class KgItemDialog extends StatefulWidget {
  final Product product;
  final CartItem? existingItem;
  final Function(Product product, {double? weightGrams, String? cartId}) onItemAdded;
  const KgItemDialog({
    Key? key, required this.product, this.existingItem, required this.onItemAdded,
  }) : super(key: key);
  @override
  State<KgItemDialog> createState() => _KgItemDialogState();
}

class _KgItemDialogState extends State<KgItemDialog> {
  final _weightController = TextEditingController();
  final _priceController = TextEditingController();
  final _weightFocusNode = FocusNode();
  final _priceFocusNode = FocusNode();
  @override
  void initState() {
    super.initState();
    if (widget.existingItem != null) {
      final initialWeight = widget.existingItem!.weightGrams;
      final initialPrice = (initialWeight / 1000) * widget.product.price;
      _weightController.text = initialWeight.toStringAsFixed(0);
      _priceController.text = initialPrice.toStringAsFixed(2);
    }
    _weightController.addListener(_onWeightChanged);
    _priceController.addListener(_onPriceChanged);
  }
  @override
  void dispose() {
    _weightController.removeListener(_onWeightChanged);
    _priceController.removeListener(_onPriceChanged);
    _weightController.dispose();
    _priceController.dispose();
    _weightFocusNode.dispose();
    _priceFocusNode.dispose();
    super.dispose();
  }
  void _onWeightChanged() {
    if (!_weightFocusNode.hasFocus) return;
    final weight = double.tryParse(_weightController.text) ?? 0;
    final price = (weight / 1000) * widget.product.price;
    _priceController.value = _priceController.value.copyWith(
      text: price.toStringAsFixed(2),
      selection: TextSelection.collapsed(offset: price.toStringAsFixed(2).length),
    );
  }
  void _onPriceChanged() {
    if (!_priceFocusNode.hasFocus) return;
    final price = double.tryParse(_priceController.text) ?? 0;
    if (widget.product.price == 0) return;
    final weight = (price / widget.product.price) * 1000;
    _weightController.value = _weightController.value.copyWith(
      text: weight.toStringAsFixed(0),
      selection: TextSelection.collapsed(offset: weight.toStringAsFixed(0).length),
    );
  }
  void _submit() {
    final weight = double.tryParse(_weightController.text) ?? 0;
    if (weight > 0) {
      widget.onItemAdded(
        widget.product, weightGrams: weight, cartId: widget.existingItem?.cartId,
      );
      Navigator.of(context).pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid weight or price.'), backgroundColor: Colors.red),
      );
    }
  }
  @override
  Widget build(BuildContext context) {
    final isEditing = widget.existingItem != null;
    return AlertDialog(
      title: Text(isEditing ? "Edit ${widget.product.name}" : "Add ${widget.product.name}"),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Price: ₹${widget.product.price.toStringAsFixed(2)} per kg", style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 24),
          TextField(
            controller: _weightController, focusNode: _weightFocusNode, autofocus: true,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Weight', suffixText: 'gm', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _priceController, focusNode: _priceFocusNode,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Price', prefixText: '₹', border: OutlineInputBorder()),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Cancel")),
        ElevatedButton(onPressed: _submit, child: Text(isEditing ? "Update" : "Add to Cart")),
      ],
    );
  }
}


// --- MAIN BILLING SCREEN ---
class BillingScreen extends StatefulWidget {
  const BillingScreen({super.key});
  @override
  State<BillingScreen> createState() => _BillingScreenState();
}

class _BillingScreenState extends State<BillingScreen> {
  List<Product> _products = [];
  List<Product> _filteredProducts = [];
  final TextEditingController _searchController = TextEditingController();

  bool _isLoading = true;
  String? _error;
  final Map<String, CartItem> _cart = {};

  final SpeechToText _speechToText = SpeechToText();
  bool _isListening = false;
  String _voiceStatus = '';
  bool _speechRecognitionAvailable = false;

  List<Outlet> _outlets = [];
  Outlet? _selectedOutlet;
  List<Staff> _staffList = [];
  Staff? _selectedStaff;
  
  bool _isConnected = true;

  static const String _malayalamLocaleId = "ml_IN";



  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _filterProducts() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredProducts = _products.where((product) {
        final productName = product.name.toLowerCase();
        return productName.contains(query);
      }).toList();
    });
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    await _checkConnectivity();

    if (!_isConnected) {
       setState(() => _isLoading = false);
      return;
    }

    await _fetchOutlets();
    if (mounted && _outlets.isNotEmpty) {
      await _showOutletSelectionDialog();
      if (_selectedOutlet != null) {
        await _fetchStaff();
        if(mounted && _staffList.isNotEmpty) {
          await _showStaffSelectionDialog();
        }
      }
    }

    if (_selectedOutlet != null && _selectedStaff != null) {
      await _fetchProducts();
      await _initializeSpeech();
    } else if (mounted && _error == null) {
       setState(() {
         _error = "Could not initialize. Please select an outlet and staff member.";
         _isLoading = false;
       });
    }
  }

  Future<void> _checkConnectivity() async {
    final connectivityResult = await (Connectivity().checkConnectivity());
    if (connectivityResult.contains(ConnectivityResult.none)) {
      setState(() {
        _isConnected = false;
        _error = "No Internet Connection. Please check your network and retry.";
      });
    } else {
       setState(() {
        _isConnected = true;
        _error = null;
      });
    }
  }

  Future<void> _fetchOutlets() async {
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/outlets/manage/'));
      if (mounted) {
        if (response.statusCode == 200) {
          final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
          setState(() {
            _outlets = data.map((json) => Outlet.fromJson(json)).where((o) => o.type == 'sales').toList();
            if(_outlets.isEmpty) {
              _error = "No sales outlets found. Please configure outlets in the Owner App.";
            }
          });
        } else {
          throw Exception('Failed to load outlets');
        }
      }
    } catch (e) {
      _showSnackBar('Failed to load outlets: $e', isError: true);
      setState(() => _error = "Could not fetch outlets. Check server connection.");
    }
  }

  Future<void> _fetchStaff() async {
    setState(() => _isLoading = true);
    try {
      // --- CORRECTED URL ---
      final response = await http.get(Uri.parse('$API_BASE_URL/staff/list/')); 
      
      if (mounted) {
        if (response.statusCode == 200) {
          final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
          setState(() {
            _staffList = data.map((json) => Staff.fromJson(json)).toList();
             if(_staffList.isEmpty) {
              _error = "No staff members found. Please add staff in the Owner App.";
            }
          });
        } else {
          throw Exception('Failed to load staff');
        }
      }
    } catch (e) {
      _showSnackBar('Failed to load staff: $e', isError: true);
      setState(() => _error = "Could not fetch staff. Check server connection.");
    } finally {
      if(mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _showOutletSelectionDialog() async {
    Outlet? temporarySelectedOutlet;
    if (_outlets.isNotEmpty) {
        temporarySelectedOutlet = _outlets[0];
    }
    
    return showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
            return StatefulBuilder(
                builder: (context, setDialogState) {
                    return AlertDialog(
                        title: const Text('Select Your Outlet'),
                        content: _outlets.isEmpty 
                            ? const Text('No sales outlets found.\nPlease add one in the Owner App.')
                            : DropdownButton<Outlet>(
                                value: temporarySelectedOutlet,
                                isExpanded: true,
                                items: _outlets.map((Outlet outlet) {
                                    return DropdownMenuItem<Outlet>(
                                        value: outlet,
                                        child: Text(outlet.name),
                                    );
                                }).toList(),
                                onChanged: (Outlet? newValue) {
                                    setDialogState(() {
                                        temporarySelectedOutlet = newValue;
                                    });
                                },
                            ),
                        actions: [
                            ElevatedButton(
                                onPressed: temporarySelectedOutlet == null ? null : () {
                                    setState(() {
                                        _selectedOutlet = temporarySelectedOutlet;
                                    });
                                    Navigator.of(context).pop();
                                },
                                child: const Text('Confirm'),
                            )
                        ],
                    );
                },
            );
        },
    );
  }

  Future<void> _showStaffSelectionDialog() async {
    Staff? temporarySelectedStaff;
     if (_staffList.isNotEmpty) {
        temporarySelectedStaff = _staffList[0];
    }

    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Select Staff Member'),
              content: _staffList.isEmpty 
                ? const Text('No staff members found.')
                : DropdownButton<Staff>(
                  value: temporarySelectedStaff,
                  isExpanded: true,
                  items: _staffList.map((Staff staff) {
                    return DropdownMenuItem<Staff>(
                      value: staff,
                      child: Text(staff.name),
                    );
                  }).toList(),
                  onChanged: (Staff? newValue) {
                    setDialogState(() {
                      temporarySelectedStaff = newValue;
                    });
                  },
                ),
              actions: [
                ElevatedButton(
                  onPressed: temporarySelectedStaff == null ? null : () {
                    setState(() {
                      _selectedStaff = temporarySelectedStaff;
                    });
                    Navigator.of(context).pop();
                  },
                  child: const Text('Confirm'),
                )
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _fetchProducts() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/items/manage-products/'));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        if (mounted) {
            setState(() {
                _products = data.map((json) => Product.fromJson(json)).toList();
                _filteredProducts = _products;
            });
        }
      } else {
        throw Exception('Failed to load products: ${response.statusCode}');
      }
    } catch (e) {
      _error = e.toString();
      _showSnackBar('Failed to load products: $e', isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }


   Future<void> _initializeSpeech() async { 
     try { 
       if (await Permission.microphone.request().isPermanentlyDenied) { 
         _showSnackBar('Microphone permission is permanently denied.', isError: true); 
         setState(() => _speechRecognitionAvailable = false); 
         return; 
       } 

       final available = await _speechToText.initialize( 
         onStatus: (status) { 
           if (!mounted) return; 
           setState(() { 
             _isListening = _speechToText.isListening; 
           }); 
         }, 
         onError: (errorNotification) { 
           if (!mounted) return; 
           setState(() { 
             _isListening = false; 
             _voiceStatus = 'Error: ${errorNotification.errorMsg}'; 
           }); 
           _showSnackBar('Voice error: ${errorNotification.errorMsg}', isError: true); 
         }, 
       ); 
       if (mounted) { 
         setState(() { 
           _speechRecognitionAvailable = available; 
           if (!available) { 
              _showSnackBar('Speech recognition not available on this device.', isError: true); 
           } 
         }); 
       } 
     } catch (e) { 
       if (mounted) { 
         setState(() => _speechRecognitionAvailable = false); 
       } 
       _showSnackBar('Could not initialize speech service: $e', isError: true); 
     } 
   }
  
  Future<void> _scanBarcode() async {
    final permission = await Permission.camera.request();
    if (!permission.isGranted) {
      _showSnackBar('Camera permission required for barcode scanning', isError: true);
      return;
    }
    try {
      final String? barcode = await Navigator.push(context, MaterialPageRoute(builder: (context) => const BarcodeScannerScreen()));
      if (barcode != null && barcode.isNotEmpty) {
        _handleBarcodeScanned(barcode);
      }
    } catch (e) {
      _showSnackBar('Barcode scanning failed: $e', isError: true);
    }
  }

  void _handleBarcodeScanned(String barcode) {
    try {
        final product = _products.firstWhere((p) => p.barcode == barcode || p.id == barcode);
        _onProductTap(product);
        _showSnackBar('Product found: ${product.name}', isError: false);
    } catch (e) {
        _showSnackBar('Product not found for barcode: $barcode', isError: true);
    }
  }

  void _onProductTap(Product product) {
    if (product.unitType == 'piece') {
      _showPieceQuantityDialog(product);
    } else {
      _showKgAddItemDialog(product);
    }
  }

  void _showPieceQuantityDialog(Product product, {CartItem? existingItem}) {
    final qtyController = TextEditingController(text: existingItem?.quantity.toString() ?? '1');
    showDialog(context: context, builder: (context) => AlertDialog(
        title: Text(existingItem != null ? "Edit ${product.name}" : "Add ${product.name}"),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('Price: ₹${product.price.toStringAsFixed(2)} per piece'),
            const SizedBox(height: 16),
            TextField(controller: qtyController, keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Quantity', border: OutlineInputBorder()),
              autofocus: true,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Cancel")),
          ElevatedButton(
            onPressed: () {
              final qty = int.tryParse(qtyController.text) ?? 0;
              if (qty > 0) {
                _addItemToCart(product, quantity: qty, existingCartId: existingItem?.cartId);
                Navigator.of(context).pop();
              } else {
                _showSnackBar('Please enter a valid quantity', isError: true);
              }
            },
            child: Text(existingItem != null ? "Update" : "Add"),
          ),
        ],
      ),
    );
  }

  void _showKgAddItemDialog(Product product, {CartItem? existingItem}) {
    showDialog(context: context, builder: (context) {
        return KgItemDialog(
          product: product, existingItem: existingItem,
          onItemAdded: (prod, {weightGrams, cartId}) {
            _addItemToCart(prod, weightGrams: weightGrams, existingCartId: cartId);
          },
        );
      },
    );
  }

  void _showCustomPriceDialog(CartItem item) {
    final priceController = TextEditingController(text: item.customPrice.toStringAsFixed(2));
    showDialog(context: context, builder: (context) => AlertDialog(
        title: Text("Edit Price for ${item.product.name}"),
        content: TextField(
          controller: priceController, keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Price', prefixText: '₹', border: OutlineInputBorder()),
          autofocus: true,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text("Cancel")),
          ElevatedButton(
            onPressed: () {
              final price = double.tryParse(priceController.text);
              if (price != null && price > 0) {
                _addItemToCart(item.product, customPrice: price, existingCartId: item.cartId);
                Navigator.of(context).pop();
              } else {
                _showSnackBar('Please enter a valid price', isError: true);
              }
            },
            child: const Text("Update"),
          ),
        ],
      ),
    );
  }

  void _editCartItem(CartItem item) {
    if (item.isByCustomPrice) {
      _showCustomPriceDialog(item);
    } else if (item.isByPiece) {
      _showPieceQuantityDialog(item.product, existingItem: item);
    } else if (item.isByWeight) {
      _showKgAddItemDialog(item.product, existingItem: item);
    }
  }

  void _addItemToCart(Product product, {int quantity = 0, double? weightGrams, double? customPrice, String? existingCartId}) {
    setState(() {
      if (existingCartId != null) {
        _cart.remove(existingCartId);
      }
      if (customPrice != null && customPrice > 0) {
          final cartId = existingCartId ?? '${product.id}_price_${DateTime.now().millisecondsSinceEpoch}';
          _cart[cartId] = CartItem(cartId: cartId, product: product, isCustomPriceItem: true, customPrice: customPrice);
      } 
      else if (product.unitType == 'piece') {
        final cartId = product.id;
        if (existingCartId == null && _cart.containsKey(cartId) && _cart[cartId]!.isByPiece) {
          _cart[cartId]!.quantity += quantity;
        } else {
          _cart[cartId] = CartItem(cartId: cartId, product: product, quantity: quantity);
        }
      } 
      else if (product.unitType == 'kg') {
        if (weightGrams != null && weightGrams > 0) {
          final cartId = existingCartId ?? '${product.id}_weight_${DateTime.now().millisecondsSinceEpoch}';
          _cart[cartId] = CartItem(cartId: cartId, product: product, weightGrams: weightGrams);
        }
      }
    });
    HapticFeedback.lightImpact();
    _showSnackBar('${product.name} ${existingCartId != null ? "updated in" : "added to"} cart', isError: false);
  }

  void _removeItemFromCart(String cartId) {
    final item = _cart[cartId];
    setState(() => _cart.remove(cartId));
    HapticFeedback.lightImpact();
    _showSnackBar('${item?.product.name} removed from cart', isError: false);
  }

  double _getCartTotal() => _cart.values.fold(0.0, (sum, item) => sum + item.total);

Future<void> _startVoiceOrder() async { 
     if (!_speechRecognitionAvailable) { 
       _showSnackBar('Speech recognition not available or permission denied.', isError: true); 
       await _initializeSpeech(); 
       return; 
     } 

     if (_isListening) { 
       await _speechToText.stop(); 
       if (mounted) setState(() => _isListening = false); 
       return; 
     } 

     if (mounted) setState(() { 
       _isListening = true; 
       _voiceStatus = 'Listening...'; 
     }); 

     try { 
       await _speechToText.listen( 
         onResult: (result) { 
           if (mounted) { 
             setState(() { 
               _voiceStatus = 'Recognized: ${result.recognizedWords}'; 
             }); 
           } 
           if (result.finalResult && result.recognizedWords.isNotEmpty) { 
             _parseAndAddVoiceOrder(result.recognizedWords); 
           } 
         }, 
         listenFor: const Duration(seconds: 15), 
         pauseFor: const Duration(seconds: 5), 
         partialResults: true, 
         localeId: _malayalamLocaleId,  
         cancelOnError: false, 
         listenMode: ListenMode.dictation, 
       ); 
     } catch (e) { 
       if (mounted) setState(() { 
         _isListening = false; 
         _voiceStatus = 'Error: $e'; 
       }); 
       _showSnackBar('Voice recognition failed: $e', isError: true); 
     } 
   }
  Future<void> _parseAndAddVoiceOrder(String spokenText) async {
    if (mounted) {
      setState(() {
        _isListening = false;
        _voiceStatus = 'Processing: "$spokenText"';
      });
    }

    try {
      final response = await http.post(
        Uri.parse('$API_BASE_URL/ownerbot/parse-order/'),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        body: jsonEncode({'text': spokenText}),
      );

      if (response.statusCode == 200) {
        final dynamic responseData = jsonDecode(utf8.decode(response.bodyBytes));

        if (responseData is Map && responseData.containsKey('error')) {
          _showSnackBar('Processing Error: ${responseData['error']}', isError: true);
          if (mounted) setState(() => _voiceStatus = 'Could not understand. Try again.');
          return;
        }

        if (responseData is! List) {
          throw Exception("Backend did not return a valid order list.");
        }

        final List<dynamic> parsedOrder = responseData;
        int itemsAdded = 0;

        for (var orderItem in parsedOrder) {
          Product product;
          try {
            product = _products.firstWhere((p) => p.id == orderItem['item_id']);
          } catch (e) {
            product = Product(
              id: 'custom_${DateTime.now().millisecondsSinceEpoch}',
              name: orderItem['name'] ?? 'Custom Amount',
              price: 0,
              unitType: 'custom',
              stock: 999,
              lowStockThreshold: 0,
            );
          }

          final double? customPrice = (orderItem['custom_price'] as num?)?.toDouble();
          final int? quantity = (orderItem['quantity'] as num?)?.toInt();
          final double? weight = (orderItem['weight_grams'] as num?)?.toDouble();
          bool wasAdded = false;

          if (customPrice != null && customPrice > 0) {
            _addItemToCart(product, customPrice: customPrice);
            wasAdded = true;
          } else if (weight != null && weight > 0) {
            _addItemToCart(product, weightGrams: weight);
            wasAdded = true;
          } else if (quantity != null && quantity > 0) {
            _addItemToCart(product, quantity: quantity);
            wasAdded = true;
          } else if (product.unitType == 'piece') {
            _addItemToCart(product, quantity: 1);
            wasAdded = true;
          }
          if (wasAdded) itemsAdded++;
        }

        if (mounted) setState(() => _voiceStatus = '');
        if (itemsAdded > 0) {
          _showSnackBar('$itemsAdded item(s) added from voice order!', isError: false);
        } else {
          _showSnackBar('Could not find any items from: "$spokenText"', isError: true);
          setState(() => _voiceStatus = 'Could not find items. Try again.');
        }
      } else {
        final errorData = jsonDecode(utf8.decode(response.bodyBytes));
        throw Exception(errorData['error'] ?? 'Failed to parse order');
      }
    } catch (e) {
      if (mounted) setState(() => _voiceStatus = 'Error processing. Check connection.');
      _showSnackBar('Could not process voice order: $e', isError: true);
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: isError ? Colors.redAccent : Colors.green,
      duration: Duration(seconds: isError ? 4 : 2),
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.all(16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      action: SnackBarAction(
        label: 'Dismiss',
        textColor: Colors.white,
        onPressed: () => ScaffoldMessenger.of(context).hideCurrentSnackBar(),
      ),
    ));
  }

  void _clearCart() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Cart'),
        content: const Text('Are you sure you want to clear all items from the cart?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () {
              setState(() => _cart.clear());
              Navigator.of(context).pop();
              _showSnackBar('Cart cleared', isError: false);
            },
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }

  Future<void> _processSale() async {
    if (_cart.isEmpty || _selectedOutlet == null || _selectedStaff == null) {
      _showSnackBar('Cart is empty or outlet/staff not selected.', isError: true);
      return;
    }

    final List<CartItem> itemsToProcess = _cart.values.toList();
    final double totalAmount = _getCartTotal();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const AlertDialog(content: Row(children: [CircularProgressIndicator(), SizedBox(width: 16), Text('Processing sale...')])),
    );

    try {
      final saleData = {
        'items': itemsToProcess.map((item) => {
              'product_id': item.product.id,
              'quantity': item.quantity,
              'weight_grams': item.weightGrams,
              'custom_price': item.isByCustomPrice ? item.customPrice : null,
              'total': item.total,
              'unit_type': item.product.unitType,
            }).toList(),
        'total_amount': totalAmount,
        'outlet_id': _selectedOutlet!.id,
        'staff_id': _selectedStaff!.id,
      };

      final response = await http.post(
        Uri.parse('$API_BASE_URL/sales/process/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(saleData),
      );

      Navigator.of(context).pop();

      if (response.statusCode == 200 || response.statusCode == 201) {
        final responseData = jsonDecode(utf8.decode(response.bodyBytes));
        final numericBillId = responseData['numeric_bill_id'];

        await showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Row(children: [Icon(Icons.check_circle, color: Colors.green), SizedBox(width: 8), Text('Sale Completed')]),
            content: Text('Sale processed successfully!\nBill No: $numericBillId\nTotal: ₹${totalAmount.toStringAsFixed(2)}'),
            actions: [
              TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('OK')),
              ElevatedButton.icon(
                icon: const Icon(Icons.print),
                onPressed: () {
                  Navigator.of(context).pop();
                  _printBill(itemsToProcess, numericBillId.toString());
                },
                label: const Text('Print Bill'),
              ),
            ],
          ),
        );

        setState(() => _cart.clear());
        _showSnackBar('Sale completed successfully!', isError: false);
        await _fetchProducts();

      } else {
        final errorData = jsonDecode(utf8.decode(response.bodyBytes));
        throw Exception(errorData['error'] ?? 'Failed to process sale');
      }
    } catch (e) {
      if (Navigator.of(context).canPop()) Navigator.of(context).pop();
      _showSnackBar('Failed to process sale: $e', isError: true);
    }
  }
  
  // --- PRINTING LOGIC ---

  final BlueThermalPrinter _printer = BlueThermalPrinter.instance;
  BluetoothDevice? _selectedPrinter;
  List<BluetoothDevice> _devices = [];

  // Your initState should look like this
@override
void initState() {
  super.initState();
  _searchController.addListener(_filterProducts);
  WidgetsBinding.instance.addPostFrameCallback((_) => _initialize());
}

  // Generates the receipt layout
  Future<List<int>> _generateReceipt(PaperSize paper, CapabilityProfile profile, List<CartItem> items, double total, Outlet? outlet, Staff? staff, String billId) async {
    final generator = Generator(paper, profile);
    List<int> bytes = [];

    bytes += generator.text('ASTHANA BAKERY', styles: const PosStyles(align: PosAlign.center, bold: true, height: PosTextSize.size2, width: PosTextSize.size2));
    bytes += generator.text('Branch: ${outlet?.name ?? 'N/A'}', styles: const PosStyles(align: PosAlign.center));
    bytes += generator.text('Phone: ${outlet?.phone ?? 'N/A'}', styles: const PosStyles(align: PosAlign.center));
    bytes += generator.hr();
    bytes += generator.row([
      PosColumn(text: 'Bill: $billId', width: 6, styles: const PosStyles(align: PosAlign.left)),
      PosColumn(text: intl.DateFormat('dd/MM/yy HH:mm').format(DateTime.now()), width: 6, styles: const PosStyles(align: PosAlign.right)),
    ]);
    bytes += generator.text('Billed By: ${staff?.name ?? 'N/A'}', styles: const PosStyles(align: PosAlign.left));
    bytes += generator.hr();
    bytes += generator.row([
      PosColumn(text: 'Item', width: 6, styles: const PosStyles(bold: true)),
      PosColumn(text: 'Qty', width: 2, styles: const PosStyles(bold: true, align: PosAlign.center)),
      PosColumn(text: 'Amount', width: 4, styles: const PosStyles(bold: true, align: PosAlign.right)),
    ]);
    bytes += generator.hr(ch: '-');

    for (var item in items) {
       bytes += generator.row([
        PosColumn(text: item.product.name, width: 6),
        PosColumn(
            text: item.isByPiece ? item.quantity.toString() : (item.isByWeight ? '${item.weightGrams.toStringAsFixed(0)}g' : '1'), 
            width: 2, 
            styles: const PosStyles(align: PosAlign.center)
        ),
        PosColumn(text: ' ${item.total.toStringAsFixed(2)}', width: 4, styles: const PosStyles(align: PosAlign.right)),
      ]);
    }
    bytes += generator.hr();
    bytes += generator.row([
      PosColumn(text: 'TOTAL', width: 4, styles: const PosStyles(bold: true, height: PosTextSize.size2, width: PosTextSize.size2)),
      PosColumn(text: 'Rs ${total.toStringAsFixed(2)}', width: 8, styles: const PosStyles(bold: true, align: PosAlign.right, height: PosTextSize.size2, width: PosTextSize.size2)),
    ]);
    bytes += generator.hr();
    bytes += generator.text('Thank You!', styles: const PosStyles(align: PosAlign.center, bold: true));
    bytes += generator.text('Visit Again', styles: const PosStyles(align: PosAlign.center));
    bytes += generator.feed(2);
    // Note: blue_thermal_printer does not have a 'cut' command, it's usually automatic.
    
    return bytes;
  }

  // Scans for and selects a Bluetooth printer
  void _scanAndSelectPrinter() async {
    try {
      _devices = await _printer.getBondedDevices();
      setState(() {}); // Update UI to show the list
    } catch (e) {
      _showSnackBar('Error fetching paired devices: $e', isError: true);
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select a Paired Printer'),
        content: SizedBox(
          width: double.maxFinite,
          child: _devices.isEmpty
              ? const Center(child: Text('No paired devices found. Please pair a printer in your device\'s Bluetooth settings.'))
              : ListView.builder(
                  itemCount: _devices.length,
                  itemBuilder: (context, index) {
                    final device = _devices[index];
                    return ListTile(
                      title: Text(device.name ?? 'Unknown Device'),
                      subtitle: Text(device.address ?? 'No Address'),
                      onTap: () {
                        setState(() {
                          _selectedPrinter = device;
                        });
                        _showSnackBar('Printer selected: ${device.name}');
                        Navigator.of(context).pop();
                      },
                    );
                  },
                ),
        ),
      ),
    );
  }

  // Connects and prints a bill via Bluetooth
  Future<void> _printDirectViaBluetooth(List<CartItem> items, double total, Outlet? outlet, Staff? staff, String billId) async {
  if (_selectedPrinter == null) {
    _showSnackBar('No printer selected!', isError: true);
    _scanAndSelectPrinter();
    return;
  }

  final isConnected = await _printer.isConnected ?? false;
  if (!isConnected) {
    try {
      await _printer.connect(_selectedPrinter!);
    } catch (e) {
      _showSnackBar('Failed to connect to printer: $e', isError: true);
      return;
    }
  }

  final paper = PaperSize.mm80;
  final profile = await CapabilityProfile.load();
  final List<int> ticketBytes = await _generateReceipt(paper, profile, items, total, outlet, staff, billId);

  // --- THIS IS THE FIX ---
  // Convert the List<int> to the required Uint8List
  try {
    await _printer.writeBytes(Uint8List.fromList(ticketBytes));
    _showSnackBar('Print command sent successfully.');
  } catch (e) {
     _showSnackBar('Error sending print command: $e', isError: true);
  }
}
  
  // Handles the "Print" button press for the current cart
  Future<void> _printBill(List<CartItem>? items, String? billId) async {
      items ??= _cart.values.toList();
      billId ??= DateTime.now().millisecondsSinceEpoch.toString().substring(6);
      
      await _printDirectViaBluetooth(items, _getCartTotal(), _selectedOutlet, _selectedStaff, billId);
  }

  // Finds and reprints a previous bill
  Future<void> _findAndReprintBill() async {
    final billNumberController = TextEditingController();
    final String? numericBillId = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reprint Bill'),
        content: TextField(controller: billNumberController, decoration: const InputDecoration(labelText: 'Enter Bill Number'), autofocus: true, keyboardType: TextInputType.number),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          ElevatedButton(onPressed: () => Navigator.of(context).pop(billNumberController.text.trim()), child: const Text('Find')),
        ],
      ),
    );

    if (numericBillId == null || numericBillId.isEmpty) return;
    
    _showSnackBar('Finding bill $numericBillId...', isError: false);

    try {
      final response = await http.get(Uri.parse('$API_BASE_URL/sales/find/$numericBillId/'));

      if (response.statusCode == 200) {
        final saleData = jsonDecode(utf8.decode(response.bodyBytes));
        final List<dynamic> itemMaps = saleData['items'];
        final List<CartItem> reprintedItems = [];
        
        for (var itemMap in itemMaps) {
          try {
            final product = _products.firstWhere(
              (p) => p.id == itemMap['product_id'],
              orElse: () => Product(
                id: itemMap['product_id'] ?? 'unknown',
                name: itemMap['name'] ?? 'Unknown Product',
                price: ((itemMap['total'] as num?)?.toDouble() ?? 0.0) / ((itemMap['quantity'] as num?)?.toInt() ?? 1),
                unitType: itemMap['unit_type'] ?? 'piece',
                stock: 0,
                lowStockThreshold: 0,
              ),
            );
            reprintedItems.add(CartItem(
              cartId: itemMap['product_id'] + '_reprint', product: product,
              quantity: (itemMap['quantity'] as num?)?.toInt() ?? 0,
              weightGrams: (itemMap['weight_grams'] as num?)?.toDouble() ?? 0.0,
              customPrice: (itemMap['custom_price'] as num?)?.toDouble() ?? 0.0,
              isCustomPriceItem: itemMap['custom_price'] != null,
            ));
          } catch (e) {
            print("Could not find product ${itemMap['product_id']} for reprinting.");
          }
        }
        
        final double total = (saleData['total_amount'] as num).toDouble();
        final String outletIdFromServer = saleData['outlet_id'] ?? '';
        final Outlet? outletForReprint = _outlets.firstWhere((o) => o.id == outletIdFromServer, orElse: () => Outlet(id: outletIdFromServer, name: outletIdFromServer));

        final String staffIdFromServer = saleData['staff_id'] ?? '';
        final Staff? staffForReprint = _staffList.firstWhere((s) => s.id == staffIdFromServer, orElse: () => Staff(id: staffIdFromServer, name: 'N/A'));

        await _printDirectViaBluetooth(reprintedItems, total, outletForReprint, staffForReprint, numericBillId);

      } else {
        final errorData = jsonDecode(utf8.decode(response.bodyBytes));
        throw Exception(errorData['error'] ?? 'Bill not found');
      }
    } catch (e) {
      _showSnackBar('Error finding bill: $e', isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final appBarTitle = _selectedOutlet == null
        ? 'Asthana Bakery POS'
        : 'POS - ${_selectedOutlet!.name} (${_selectedStaff?.name ?? "No Staff"})';

    return Scaffold(
      appBar: AppBar(
        title: Text(appBarTitle),
        actions: [
          IconButton(icon: Icon(Icons.print_outlined, color: _selectedPrinter != null ? Colors.lightGreenAccent : Colors.white), onPressed: _scanAndSelectPrinter, tooltip: "Select Printer"),
          IconButton(icon: const Icon(Icons.receipt_long_outlined), onPressed: (_selectedOutlet == null || _selectedStaff == null) ? null : _findAndReprintBill, tooltip: "Find Bill"),
          IconButton(icon: const Icon(Icons.qr_code_scanner), onPressed: (_selectedOutlet == null || _selectedStaff == null) ? null : _scanBarcode, tooltip: "Scan Barcode"),
          if (_speechRecognitionAvailable)
            Stack(
              alignment: Alignment.center,
              children: [
                IconButton(
                  icon: Icon(_isListening ? Icons.mic : Icons.mic_none, color: _isListening ? Colors.redAccent : Colors.white),
                  onPressed: (_selectedOutlet == null || _selectedStaff == null) ? null : _startVoiceOrder,
                  tooltip: "Voice Order",
                ),
                if (_isListening)
                  SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation<Color>(Colors.red.shade200)),
                  ),
              ],
            ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: (_selectedOutlet == null || _selectedStaff == null) ? null : _fetchProducts, tooltip: "Refresh Products"),
        ],
      ),
      body: !_isConnected 
        ? Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.signal_wifi_off, size: 80, color: Colors.grey),
                const SizedBox(height: 20),
                Text(_error ?? 'No Internet Connection', style: Theme.of(context).textTheme.headlineSmall, textAlign: TextAlign.center),
                const SizedBox(height: 20),
                ElevatedButton.icon(icon: const Icon(Icons.refresh), onPressed: _initialize, label: const Text('Retry Connection'))
              ],
            ),
          )
        : (_selectedOutlet == null || _selectedStaff == null)
          ? Center(
              child: _isLoading 
              ? const CircularProgressIndicator() 
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Text(_error ?? 'Please select an outlet and staff member to begin.', textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleMedium),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.store),
                      onPressed: _initialize, 
                      label: const Text('Start Setup')
                    )
                  ],
                )
            )
          : LayoutBuilder(
              builder: (context, constraints) {
                final isWideScreen = constraints.maxWidth > 800;
                
                Widget bodyContent;

                if (_isLoading) {
                  bodyContent = const Center(child: CircularProgressIndicator());
                } else if (_error != null) {
                  bodyContent = Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.error, size: 64, color: Colors.red),
                    const SizedBox(height: 16),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16.0),
                      child: Text("Error: $_error", textAlign: TextAlign.center),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(onPressed: _fetchProducts, child: const Text('Retry')),
                  ]));
                } else {
                  bodyContent = Column(
                    children: [
                      Padding(
                        padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
                        child: TextField(
                          controller: _searchController,
                          decoration: InputDecoration(
                            hintText: 'Search for products...',
                            prefixIcon: const Icon(Icons.search),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide.none,
                            ),
                            filled: true,
                            fillColor: Colors.white,
                            contentPadding: EdgeInsets.zero,
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.clear),
                                    onPressed: () {
                                      _searchController.clear();
                                    },
                                  )
                                : null,
                          ),
                        ),
                      ),
                      Expanded(
                        child: ProductGrid(
                          products: _filteredProducts,
                          onProductTap: _onProductTap,
                          showSnackBar: _showSnackBar,
                        ),
                      ),
                    ],
                  );
                }

                if (isWideScreen) {
                  return Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: Column(
                          children: [
                            if (_voiceStatus.isNotEmpty)
                              Container(
                                color: Colors.amber.shade100,
                                padding: const EdgeInsets.all(12.0),
                                child: Center(child: Text(_voiceStatus, style: const TextStyle(fontWeight: FontWeight.bold))),
                              ),
                            Expanded(child: bodyContent),
                          ],
                        ),
                      ),
                      SizedBox(
                        width: 400,
                        child: CartPanel(
                          cart: _cart,
                          getCartTotal: _getCartTotal,
                          onClearCart: _clearCart,
                          onEditItem: _editCartItem,
                          onRemoveItem: _removeItemFromCart,
                          onPrintBill: () => _printBill(null, null),
                          onProcessSale: _processSale,
                        ),
                      ),
                    ],
                  );
                } else {
                  return Column(
                    children: [
                      if (_voiceStatus.isNotEmpty)
                        Container(
                          color: Colors.amber.shade100,
                          padding: const EdgeInsets.all(12.0),
                          child: Center(child: Text(_voiceStatus, style: const TextStyle(fontWeight: FontWeight.bold))),
                        ),
                      Expanded(child: bodyContent),
                    ],
                  );
                }
              },
            ),
      floatingActionButton: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth > 800 || _selectedOutlet == null || _selectedStaff == null) {
            return const SizedBox.shrink();
          }
          return FloatingActionButton.extended(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => CartScreen(
                    cart: _cart,
                    getCartTotal: _getCartTotal,
                    onClearCart: () {
                      _clearCart();
                      if (Navigator.canPop(context)) Navigator.pop(context);
                    },
                    onEditItem: _editCartItem,
                    onRemoveItem: (cartId) => setState(() => _removeItemFromCart(cartId)),
                    onPrintBill: () => _printBill(null, null),
                    onProcessSale: () async {
                      await _processSale();
                      if (_cart.isEmpty && Navigator.canPop(context)) {
                        Navigator.pop(context);
                      }
                    },
                  ),
                ),
              ).then((_) => setState(() {}));
            },
            icon: const Icon(Icons.shopping_cart_outlined),
            backgroundColor: Theme.of(context).colorScheme.primary,
            foregroundColor: Colors.white,
            label: Text(
              _cart.isEmpty 
              ? 'View Bill' 
              : 'Bill (${_cart.length}) - ₹${_getCartTotal().toStringAsFixed(0)}',
            ),
          );
        },
      ),
    );
  }
}


class ProductGrid extends StatelessWidget {
  final List<Product> products;
  final Function(Product) onProductTap;
  final Function(String, {bool isError}) showSnackBar;

  const ProductGrid({
    Key? key,
    required this.products,
    required this.onProductTap,
    required this.showSnackBar,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width > 600;
    
    if (products.isEmpty) {
      return const Center(
        child: Text(
          'No products found.',
          style: TextStyle(fontSize: 18, color: Colors.grey),
        ),
      );
    }
    
    return GridView.builder(
      padding: const EdgeInsets.all(12),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: isWide ? 4 : 3,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 0.85,
      ),
      itemCount: products.length,
      itemBuilder: (context, index) {
        final product = products[index];
        final isOutOfStock = product.unitType == 'piece' && product.stock <= 0;
        final isLowStock = product.unitType == 'piece' && !isOutOfStock && product.stock <= product.lowStockThreshold;

        Color stockColor = Colors.green.shade700;
        if (isLowStock) stockColor = Colors.orange.shade800;
        if (isOutOfStock) stockColor = Colors.red.shade700;

        return Opacity(
          opacity: isOutOfStock ? 0.6 : 1.0,
          child: Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: isOutOfStock
                  ? () => showSnackBar('${product.name} is out of stock.', isError: true)
                  : () => onProductTap(product),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      color: Colors.white,
                      child: Center(
                        child: (product.img.isNotEmpty && Uri.tryParse(product.img)?.hasAbsolutePath == true && (product.img.startsWith('http://') || product.img.startsWith('https://')))
                            ? Image.network(
                                product.img,
                                fit: BoxFit.cover,
                                errorBuilder: (c, o, s) => const Icon(Icons.cake, color: Colors.brown, size: 40)
                              )
                            : CircleAvatar(
                                radius: 30,
                                backgroundColor: Colors.brown.shade100,
                                child: Text(
                                  product.name.isNotEmpty ? product.name[0].toUpperCase() : '?',
                                  style: const TextStyle(fontSize: 24, color: Colors.brown, fontWeight: FontWeight.bold)
                                )
                              ),
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.all(8.0),
                    decoration: BoxDecoration(color: Colors.black.withOpacity(0.04)),
                    child: Column(
                      children: [
                        Text(product.name, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis),
                        const SizedBox(height: 2),
                        Text(product.unitType == 'piece' ? '₹${product.price.toStringAsFixed(2)}/pc' : '₹${product.price.toStringAsFixed(2)}/kg', style: TextStyle(color: Theme.of(context).primaryColor, fontWeight: FontWeight.w600, fontSize: 11)),
                        if (product.unitType == 'piece') ...[
                          const SizedBox(height: 2),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(color: stockColor.withOpacity(0.15), borderRadius: BorderRadius.circular(5)),
                            child: Text(isOutOfStock ? 'OUT OF STOCK' : 'Stock: ${product.stock}', style: TextStyle(color: stockColor, fontWeight: FontWeight.bold, fontSize: 10)),
                          ),
                        ]
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class CartPanel extends StatelessWidget {
  final Map<String, CartItem> cart;
  final double Function() getCartTotal;
  final VoidCallback onClearCart;
  final Function(CartItem) onEditItem;
  final Function(String) onRemoveItem;
  final Future<void> Function() onPrintBill;
  final Future<void> Function() onProcessSale;

  const CartPanel({
    Key? key,
    required this.cart,
    required this.getCartTotal,
    required this.onClearCart,
    required this.onEditItem,
    required this.onRemoveItem,
    required this.onPrintBill,
    required this.onProcessSale,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 10, offset: const Offset(-2, 0))]
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(color: Colors.white, border: Border(bottom: BorderSide(color: Colors.grey.shade200))),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Current Bill", style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                if (cart.isNotEmpty)
                  IconButton(icon: const Icon(Icons.clear_all, color: Colors.red), onPressed: onClearCart, tooltip: 'Clear Cart'),
              ],
            ),
          ),
          Expanded(
            child: cart.isEmpty
                ? Center(
                    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Icon(Icons.shopping_cart_outlined, size: 64, color: Colors.grey.shade400),
                      const SizedBox(height: 16),
                      Text("Cart is empty", style: TextStyle(color: Colors.grey.shade600, fontSize: 16)),
                    ]),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: cart.length,
                    itemBuilder: (context, index) {
                      final cartId = cart.keys.elementAt(index);
                      final item = cart[cartId]!;
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        elevation: 1.5,
                        child: ListTile(
                          title: Text(item.product.name, style: const TextStyle(fontWeight: FontWeight.w500)),
                          subtitle: Text(item.displayPrice, style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text('₹${item.total.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                              const SizedBox(width: 8),
                              IconButton(icon: const Icon(Icons.delete, color: Colors.redAccent, size: 20), onPressed: () => onRemoveItem(cartId)),
                            ],
                          ),
                          onTap: () => onEditItem(item),
                        ),
                      );
                    },
                  ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: Colors.grey.shade200))),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("Total (${cart.length} items)", style: Theme.of(context).textTheme.titleLarge),
                    Text('₹${getCartTotal().toStringAsFixed(2)}', style: Theme.of(context).textTheme.titleLarge?.copyWith(color: Colors.green.shade800, fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(child: OutlinedButton.icon(icon: const Icon(Icons.print), label: const Text("Print"), onPressed: cart.isEmpty ? null : onPrintBill)),
                    const SizedBox(width: 12),
                    Expanded(flex: 2, child: ElevatedButton.icon(icon: const Icon(Icons.payment), label: const Text("Complete Sale"), onPressed: cart.isEmpty ? null : onProcessSale)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class CartScreen extends StatefulWidget {
  final Map<String, CartItem> cart;
  final double Function() getCartTotal;
  final VoidCallback onClearCart;
  final Function(CartItem) onEditItem;
  final Function(String) onRemoveItem;
  final Future<void> Function() onPrintBill;
  final Future<void> Function() onProcessSale;

  const CartScreen({
    Key? key,
    required this.cart,
    required this.getCartTotal,
    required this.onClearCart,
    required this.onEditItem,
    required this.onRemoveItem,
    required this.onPrintBill,
    required this.onProcessSale,
  }) : super(key: key);

  @override
  _CartScreenState createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Current Bill"),
        actions: [
          if (widget.cart.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.clear_all),
              onPressed: () {
                widget.onClearCart();
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (widget.cart.isEmpty && Navigator.canPop(context)) {
                    Navigator.pop(context);
                  } else {
                      setState(() {});
                  }
                });
              },
              tooltip: "Clear Cart",
            )
        ],
      ),
      body: CartPanel(
        cart: widget.cart,
        getCartTotal: widget.getCartTotal,
        onClearCart: widget.onClearCart,
        onEditItem: (item) {
          widget.onEditItem(item);
          setState(() {});
        },
        onRemoveItem: (cartId) {
          widget.onRemoveItem(cartId);
          setState(() {});
        },
        onPrintBill: widget.onPrintBill,
        onProcessSale: widget.onProcessSale,
      ),
    );
  }
}