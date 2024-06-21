import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_facebook_auth/flutter_facebook_auth.dart';
import 'package:flutter_wechat_auth/flutter_wechat_auth.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

class LoginPage extends StatelessWidget {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();

  Future<void> _signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser != null) {
        final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
        final AuthCredential credential = GoogleAuthProvider.credential(
          accessToken: googleAuth.accessToken,
          idToken: googleAuth.idToken,
        );
        final UserCredential userCredential = await _auth.signInWithCredential(credential);
        print("Google sign in successful: ${userCredential.user?.displayName}");
      }
    } catch (e) {
      print("Google sign in failed: $e");
    }
  }

  Future<void> _signInWithFacebook() async {
    try {
      final LoginResult result = await FacebookAuth.instance.login();
      if (result.status == LoginStatus.success) {
        final OAuthCredential credential = FacebookAuthProvider.credential(accessToken.token);
        final UserCredential userCredential = await _auth.signInWithCredential(credential);
        print("Facebook sign in successful: ${userCredential.user?.displayName}");
      }
    } catch (e) {
      print("Facebook sign in failed: $e");
    }
  }

  Future<void> _signInWithApple() async {
    try {
      final AuthorizationCredentialAppleID appleIDCredential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
      );

      final OAuthCredential credential = OAuthProvider("apple.com").credential(
        idToken: appleIDCredential.identityToken,
        accessToken: appleIDCredential.authorizationCode,
      );

      final UserCredential userCredential = await _auth.signInWithCredential(credential);
      print("Apple sign in successful: ${userCredential.user?.displayName}");
    } catch (e) {
      print("Apple sign in failed: $e");
    }
  }

  Future<void> _signInWithWeChat() async {
    try {
      final WechatAuthResult result = await FlutterWechatAuth.auth(
        appId: 'your_wechat_app_id',
        universalLink: 'your_universal_link',
      );

      if (result.status == WechatAuthStatus.success) {
        final AuthCredential credential = WeChatAuthProvider.credential(result.code);
        final UserCredential userCredential = await _auth.signInWithCredential(credential);
        print("WeChat sign in successful: ${userCredential.user?.displayName}");
      }
    } catch (e) {
      print("WeChat sign in failed: $e");
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.close, color: Colors.black),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              'Profile',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 16),
            Text(
              'Sign in to Your Account',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 32),
            SignInButton(
              icon: FontAwesomeIcons.google,
              text: 'Sign in with Google',
              color: Colors.white,
              textColor: Colors.black,
              onPressed: _signInWithGoogle,
            ),
            SizedBox(height: 16),

            SignInButton(
              icon: FontAwesomeIcons.facebook,
              text: 'Sign in with Facebook',
              color: Colors.white,
              textColor: Colors.black,
              onPressed: _signInWithFacebook,
            ),
            SizedBox(height: 16),
            
            SignInButton(
              icon: FontAwesomeIcons.apple,
              text: 'Sign in with Apple',
              color: Colors.white,
              textColor: Colors.black,
              onPressed: _signInWithApple,
            ),
            SizedBox(height: 16),
          
            SignInButton(
              icon: FontAwesomeIcons.weixin,
              text: 'Sign in with Wechat',
              color: Colors.white,
              textColor: Colors.black,
              onPressed: _signInWithWeChat,
            ),
            
          ],
        ),
      ),
    );
  }
}

class SignInButton extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color color;
  final Color textColor;
  final VoidCallback onPressed;

  SignInButton({
    required this.icon,
    required this.text,
    required this.color,
    required this.textColor,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0), // 增加按钮和页面边界之间的间距
      child: Container(
        height: 50,
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey),
          borderRadius: BorderRadius.circular(8),
        ),
        child: ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: color, // 更新参数名为 backgroundColor
            foregroundColor: textColor, // 更新参数名为 foregroundColor
            minimumSize: Size(double.infinity, 50),
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          icon: Icon(icon, size: 24, color: textColor),
          label: Text(
            text,
            style: TextStyle(fontSize: 16, color: textColor),
          ),
          onPressed: onPressed,
        ),
      ),
    );
  }
}
