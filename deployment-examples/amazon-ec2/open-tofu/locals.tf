locals {

  ssh_pub_key = file("../keys/aws.pem.pub")

aws_user_data_template = templatefile(
               "./startup.tftpl",
               {
                   key   = local.ssh_pub_key
                 
               }
              )


}