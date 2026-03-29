def test_login_me_and_change_password_flow(client):
    login_response = client.post("/auth/login", json={"username": "admin", "password": "admin12345"})
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["user"]["username"] == "admin"
    assert login_payload["user"]["must_change_password"] is True

    headers = {"Authorization": f"Bearer {login_payload['access_token']}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["display_name"] == "Quản trị viên kiểm thử"

    change_password_response = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "admin12345", "new_password": "Admin56789"},
    )
    assert change_password_response.status_code == 200
    assert "Đã cập nhật mật khẩu" in change_password_response.json()["message"]

    relogin_response = client.post("/auth/login", json={"username": "admin", "password": "Admin56789"})
    assert relogin_response.status_code == 200
    assert relogin_response.json()["user"]["must_change_password"] is False


def test_admin_can_create_list_and_reset_user(client, auth_headers):
    create_response = client.post(
        "/users/",
        headers=auth_headers,
        json={
            "username": "operator1",
            "display_name": "Nhân viên vận hành",
            "password": "Operator123",
            "role": "operator",
        },
    )
    assert create_response.status_code == 200
    created_user = create_response.json()["user"]
    assert created_user["username"] == "operator1"
    assert created_user["role"] == "operator"

    list_response = client.get("/users/", headers=auth_headers)
    assert list_response.status_code == 200
    usernames = [user["username"] for user in list_response.json()["users"]]
    assert usernames == ["admin", "operator1"]

    reset_response = client.post(f"/users/{created_user['id']}/reset-password", headers=auth_headers)
    assert reset_response.status_code == 200
    temporary_password = reset_response.json()["temporary_password"]
    assert len(temporary_password) >= 12

    operator_login = client.post(
        "/auth/login",
        json={"username": "operator1", "password": temporary_password},
    )
    assert operator_login.status_code == 200
    assert operator_login.json()["user"]["must_change_password"] is True


def test_admin_can_delete_user(client, auth_headers):
    create_response = client.post(
        "/users/",
        headers=auth_headers,
        json={
            "username": "operator2",
            "display_name": "Nhân viên cũ",
            "password": "Operator123",
            "role": "operator",
        },
    )
    assert create_response.status_code == 200
    created_user = create_response.json()["user"]

    delete_response = client.delete(f"/users/{created_user['id']}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert "Đã xóa người dùng 'operator2'" in delete_response.json()["message"]

    list_response = client.get("/users/", headers=auth_headers)
    assert list_response.status_code == 200
    usernames = [user["username"] for user in list_response.json()["users"]]
    assert usernames == ["admin"]


def test_admin_cannot_delete_current_account(client, auth_headers):
    list_response = client.get("/users/", headers=auth_headers)
    assert list_response.status_code == 200
    admin_user = next(user for user in list_response.json()["users"] if user["username"] == "admin")

    delete_response = client.delete(f"/users/{admin_user['id']}", headers=auth_headers)
    assert delete_response.status_code == 400
    assert delete_response.json()["detail"] == "Không thể xóa tài khoản đang đăng nhập."
